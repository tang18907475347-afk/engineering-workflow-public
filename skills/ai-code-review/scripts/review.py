#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Code Review 的本地确定性工具。

负责：
1. 读取并规范化平台后端返回的 AI 评审评论；
2. 生成 review.json 骨架（分析由 Agent 填写）；
3. 用字段 patch 批量更新 analysis、重算指纹、原子写入；
4. 校验 Decision Envelope；
5. 以 dry-run 为默认，提交 reply / feedback。

finding 是否成立、是否修复由 Agent 依据代码与证据判断；本脚本不自动改代码，
也不维护第二份人工决策文件。平台反馈与修复决策是两件事，默认不互相绑定。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import mr_backend  # 平台后端（占位）：唯一需要你替换的远程传输层
import review_contract


class ReviewError(RuntimeError):
    """输入、状态或平台响应不满足预期。"""


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
SEVERITY_LABEL = {"high": "高", "medium": "中", "low": "低", "unknown": "?"}
SEVERITY_ALIASES = {
    "高": "high", "中": "medium", "低": "low",
    "high": "high", "medium": "medium", "low": "low",
    "critical": "high", "warning": "medium", "info": "low",
}
ACTIONS = ("adopt", "ignore", "reject")
REASON_CODES = {
    "reject": {
        "AI_MISJUDGED", "SCENARIO_IMPOSSIBLE", "NOT_APPLICABLE",
        "RULE_DISAGREE", "MY_IMPL_BETTER", "SUGGESTION_POOR",
    },
    "ignore": {"LOW_PRIORITY", "KNOWN_ISSUE", "TEMP_CODE"},
}
ANALYSIS_FIELDS = {
    "issueRisk", "assessment", "recommendation",
    "trigger", "impact", "rootCause", "evidence", "openQuestions", "proposal",
}
PROPOSAL_FIELDS = {
    "summary", "approach", "files", "owner", "changes", "verification",
    "scope", "fixRisk", "alternatives", "requiresHumanAcceptance",
}
PATCH_FORBIDDEN_FIELDS = {
    "source", "id", "reviewKey", "proposalFingerprint",
    "decision", "status", "note",
}


def _iso(value) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M")
    return str(value) if value else ""


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _truncate(text: str, limit: int) -> str:
    compact = " ".join((text or "").split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def parse_badge(note: str) -> tuple[str, str, str]:
    """从 `![缺陷 · 中](...)` 解析 category / severity / title。"""
    text = (note or "").strip()
    match = re.match(r"!\[([^\]]*)\]\(([^)]*)\)", text)
    if not match:
        return "unknown", "unknown", _first_line(text)
    alt = match.group(1).strip()
    rest = text[match.end():].strip()
    parts = [part.strip() for part in re.split(
        r"\s*[·|]\s*", alt) if part.strip()]
    category = parts[0] if parts else "unknown"
    raw_severity = parts[1] if len(parts) > 1 else "unknown"
    severity = SEVERITY_ALIASES.get(
        raw_severity.lower(), SEVERITY_ALIASES.get(raw_severity, "unknown"))
    return category, severity, _first_line(rest) or alt


def parse_context(value: str) -> tuple[str | None, str | None]:
    parts = (value or "").split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return None, parts[0]
    return None, None


def platform_state(adopted, closed) -> str:
    if adopted == 1 and closed == 0:
        return "pending"
    if closed == 1 or (adopted is not None and adopted != 1):
        return "handled"
    return "unknown"


def platform_kind(adopted, closed) -> str:
    """CLI 用的粗粒度 kind；唯一解释源仍是 review_contract.platform_interpretation。

    kind 只是 interpretation 的归并标签，不再重新解读 adopted/closed 语义。
    """
    return {
        "PENDING": "pending",
        "IGNORED": "ignored",
        "CLOSED_NOT_ADOPTED": "closed",
        "CLOSED_WITH_ACTION": "closed",
        "UNKNOWN": "unknown",
    }[review_contract.platform_interpretation(adopted, closed)]


def normalize_comment(raw: dict, head_sha: str | None = None) -> dict:
    note = raw.get("note") or raw.get("body") or ""
    category, severity, title = parse_badge(note)
    adopted = raw.get("adopted")
    closed = raw.get("closed")
    path = raw.get("path") or raw.get("filePath") or ""
    line = raw.get("line")
    if line is None:
        line = raw.get("lineNumber")
    line_range = raw.get("lineRange") or raw.get("originLineRange") or {}
    if line is None and line_range:
        line = line_range.get("toLine") or line_range.get("fromLine")
    context = raw.get("context") or ""
    old_sha, new_sha = parse_context(context)
    head_matches = None
    if head_sha and new_sha:
        left, right = head_sha.lower(), new_sha.lower()
        head_matches = left.startswith(right) or right.startswith(left)

    if "aiComment" in raw:
        ai_comment = bool(raw.get("aiComment"))
    elif "isAiComment" in raw:
        ai_comment = bool(raw.get("isAiComment"))
    else:
        ai_comment = False

    author = raw.get("coAuthor") or raw.get("author") or {}
    author_name = author.get("username") or author.get("name") or ""
    suggestion = raw.get("suggestion")
    if not isinstance(suggestion, dict):
        suggestion = None

    return {
        "id": raw.get("id"),
        "state": platform_state(adopted, closed),
        "kind": platform_kind(adopted, closed),
        "interpretation": review_contract.platform_interpretation(adopted, closed),
        "category": category,
        "severity": severity,
        "severity_label": SEVERITY_LABEL.get(severity, "?"),
        "title": title,
        "path": path,
        "line": line,
        "line_range": line_range,
        "side": raw.get("side"),
        "outdated": bool(raw.get("outdated")),
        "parent_note_id": raw.get("parentNoteId"),
        "ai_comment": ai_comment,
        "platform": {"adopted": adopted, "closed": closed},
        "author": author_name,
        "created_at": _iso(raw.get("createdAt") or raw.get("created_at")),
        "updated_at": _iso(raw.get("updatedAt") or raw.get("updated_at")),
        "context": context,
        "old_sha": old_sha,
        "new_sha": new_sha,
        "head_matches": head_matches,
        "suggestion": suggestion,
        "diff_context": raw.get("notesCodeDiffContext") or "",
        "note": note,
    }


def fetch_comments(repo: str, mr: int, runner=None) -> list[dict]:
    runner = runner or mr_backend.run_tool
    data = runner("list_merge_request_ai_comments",
                  {"repo": repo, "mergeRequestId": mr})
    if data is None:
        return []
    if isinstance(data, dict):
        if isinstance(data.get("list"), list):
            data = data["list"]
        elif data.get("error"):
            raise ReviewError(str(data["error"]))
        else:
            raise ReviewError(
                "AI 评论列表响应不是数组："
                + json.dumps(data, ensure_ascii=False)[:300])
    if not isinstance(data, list):
        raise ReviewError(f"AI 评论列表响应类型异常：{type(data).__name__}")
    return [item for item in data if isinstance(item, dict)]


def find_comment(comments: list[dict], note_id: int) -> dict:
    for comment in comments:
        if comment.get("id") == note_id:
            return comment
    raise ReviewError(
        f"AI 评论 {note_id} 不在该 MR 的 AI 评论列表中；"
        "确认 note id、repo 与项目级 mergeRequestId")


def _parse_severities(value: str | None) -> set[str] | None:
    if not value:
        return None
    items = {item.strip().lower() for item in value.split(",") if item.strip()}
    unknown = sorted(item for item in items if item not in SEVERITY_ORDER)
    if unknown:
        raise ReviewError(
            f"未知 severity：{', '.join(unknown)}；可用：high,medium,low")
    return items


def _parse_ids(value: str | None) -> set[int] | None:
    if not value:
        return None
    try:
        return {int(item.strip()) for item in value.split(",") if item.strip()}
    except ValueError as exc:
        raise ReviewError("--ids 必须是逗号分隔的整数") from exc


def filter_comments(comments: list[dict], state: str = "pending",
                    severities: set[str] | None = None, path: str | None = None,
                    ids: set[int] | None = None, limit: int | None = None) -> list[dict]:
    result = []
    for comment in comments:
        if state == "all":
            pass
        elif state in ("pending", "handled"):
            if comment["state"] != state:
                continue
        elif comment.get("kind") != state:
            continue
        if severities and comment["severity"] not in severities:
            continue
        if path and path.lower() not in (comment["path"] or "").lower():
            continue
        if ids and comment["id"] not in ids:
            continue
        result.append(comment)
    result.sort(key=lambda item: (
        SEVERITY_ORDER.get(item["severity"], 3), item.get("id") or 0))
    if limit:
        result = result[:limit]
    return result


def _counts(comments: list[dict]) -> dict:
    states = Counter(comment["state"] for comment in comments)
    kinds = Counter(comment.get("interpretation") or "UNKNOWN"
                    for comment in comments)
    severities = Counter(comment["severity"] for comment in comments)
    return {
        "states": dict(sorted(states.items())),
        "kinds": dict(sorted(kinds.items())),
        "severities": dict(sorted(severities.items())),
    }


def normalize_repo(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    text = re.sub(r"^git@[^:]+:", "", text)
    text = re.sub(r"^ssh://[^/]+/", "", text)
    text = re.sub(r"^https?://[^/]+/", "", text)
    text = text.rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    return text or None


def _git(worktree: str | Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(worktree), *args],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def git_remote(worktree: str | Path) -> str | None:
    return _git(worktree, "remote", "get-url", "origin")


def git_head(worktree: str | Path) -> str | None:
    return _git(worktree, "rev-parse", "HEAD")


def git_branch(worktree: str | Path) -> str | None:
    return _git(worktree, "rev-parse", "--abbrev-ref", "HEAD")


def git_status(worktree: str | Path) -> str | None:
    """返回 porcelain 输出；干净仓库返回空串，无法判断返回 None。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(worktree), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip()


def _remote_host(remote: str | None) -> str | None:
    if not remote:
        return None
    text = remote.strip()
    if text.startswith("git@"):
        rest = text[4:]
        if ":" in rest:
            return rest.split(":", 1)[0] or None
    if "://" in text:
        rest = text.split("://", 1)[1]
        if rest.startswith("git@"):
            rest = rest[4:]
        return rest.split("/", 1)[0] or None
    return None


def mr_web_url(repo: str, iid, worktree: str | Path | None = None,
               base_url: str | None = None) -> str | None:
    """优先从平台 webUrl 构造 MR 页面；它常是项目首页，不能直接当 MR 链接。"""
    if iid is None:
        return None
    if base_url:
        base = str(base_url).strip().rstrip("/")
        if "/-/merge_requests/" in base:
            return base
        if "://" in base:
            return f"{base}/-/merge_requests/{iid}"
    host = _remote_host(git_remote(worktree)) if worktree else None
    default_host = os.environ.get("GITLAB_HOST", "gitlab.com")
    return f"https://{host or default_host}/{repo}/-/merge_requests/{iid}"


def resolve_repo(repo: str | None, worktree: str | Path) -> str:
    if repo:
        normalized = normalize_repo(repo)
        if not normalized or "/" not in normalized:
            raise ReviewError(f"无效 repo：{repo!r}；应为 foo/bar 形式")
        return normalized
    normalized = normalize_repo(git_remote(worktree))
    if not normalized or "/" not in normalized:
        raise ReviewError("无法从 --worktree 的 origin 推断 repo；请显式传 --repo")
    return normalized


def worktree_state(worktree: str | Path, repo: str) -> dict:
    remote = normalize_repo(git_remote(worktree))
    matches = None if remote is None else remote == repo
    return {
        "repo": remote,
        "head": git_head(worktree) if matches else None,
        "branch": git_branch(worktree) if matches else None,
        "matches": matches,
    }


def _render_table(comments: list[dict]) -> str:
    headers = ("ID", "SEV", "STATE", "KIND", "OUTDATED", "LOCATION", "TITLE")
    rows = []
    for comment in comments:
        location = comment["path"] or "-"
        if comment.get("line") is not None:
            location = f"{location}:{comment['line']}"
        platform = comment.get("platform") or {}
        kind_cell = (f"{comment.get('interpretation', '?')}"
                     f" {platform.get('adopted', '?')}/{platform.get('closed', '?')}")
        rows.append((
            str(comment["id"]),
            comment["severity"],
            comment["state"],
            _truncate(kind_cell, 28),
            "yes" if comment["outdated"] else "no",
            _truncate(location, 48),
            _truncate(comment["title"], 56),
        ))
    widths = [max([len(header)] + [len(row[index]) for row in rows])
              for index, header in enumerate(headers)]
    lines = ["  ".join(header.ljust(widths[index])
                       for index, header in enumerate(headers))]
    lines.append("  ".join("-" * width for width in widths))
    for row in rows:
        lines.append("  ".join(row[index].ljust(widths[index])
                               for index in range(len(headers))))
    return "\n".join(lines)


def _print_list(repo: str, mr: int, comments: list[dict],
                filtered: list[dict], worktree: dict,
                branch: str | None = None) -> None:
    print(f"repo={repo}  mr={mr}")
    if worktree.get("matches") is False:
        print(f"worktree={worktree.get('repo') or '?'}（与 MR 仓库不同，未比较 HEAD）")
    elif worktree.get("head"):
        label = f" ({branch})" if branch else ""
        print(f"worktree HEAD={worktree['head'][:12]}{label}")
    print(f"AI comments: total={len(comments)}  matched={len(filtered)}")
    total_counts = _counts(comments)
    print("all states:", ", ".join(
        f"{key}={value}" for key, value in total_counts["states"].items()) or "-")
    print("all kinds:", ", ".join(
        f"{key}={value}" for key, value in total_counts["kinds"].items()) or "-")
    print("matched severity:", ", ".join(
        f"{key}={value}" for key, value in _counts(filtered)["severities"].items()) or "-")
    mismatched = [comment for comment in filtered
                  if comment.get("head_matches") is False]
    if mismatched:
        print(f"WARN: {len(mismatched)} 条评论 context 与当前 HEAD 不一致；"
              "先切到 source branch，或核对证据是否仍适用。")
        for comment in mismatched[:5]:
            review_sha = comment.get("new_sha") or "?"
            print(f"  - {comment['id']} review={review_sha[:12]}")
    if filtered:
        print()
        print(_render_table(filtered))
    else:
        print()
        print("(没有匹配的 AI 评论；可用 --state all 查看已处理项)")


def _print_dry_run(tool: str, payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"dry_run": True, "tool": tool, "payload": payload},
                         ensure_ascii=False, indent=2))
        return
    print(f"[dry-run] {tool}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("未写入。确认后加 --confirm。")


def _print_write_result(tool: str, payload: dict, result, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"dry_run": False, "tool": tool, "payload": payload,
                          "result": result}, ensure_ascii=False, indent=2))
        return
    print(f"[ok] {tool}")
    if isinstance(result, str):
        print(result[:2000])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
    print("提示：接口成功只表示反馈已提交；重新 list 查看平台状态，"
          "代码是否修好由本地验证决定。")


def cmd_mr(args, runner=None) -> int:
    runner = runner or mr_backend.run_tool
    repo = resolve_repo(args.repo, args.worktree)
    detail = runner("get_merge_request_detail",
                    {"repo": repo, "mergeRequestId": args.mr})
    files = runner("list_merge_request_changed_files",
                   {"repo": repo, "mergeRequestId": args.mr})
    if not isinstance(detail, dict):
        detail = {}
    if not isinstance(files, dict):
        files = {}
    iid = detail.get("iid")
    mr_url = mr_web_url(repo, iid, args.worktree,
                        base_url=detail.get("webUrl"))
    summary = {
        "repo": repo,
        "mergeRequestId": args.mr,
        "id": detail.get("id"),
        "iid": iid,
        "state": detail.get("state"),
        "title": detail.get("title"),
        "sourceBranch": detail.get("sourceBranch"),
        "targetBranch": detail.get("targetBranch"),
        "mergeStatus": detail.get("mergeStatus"),
        "webUrl": mr_url,
        "projectUrl": detail.get("webUrl"),
        "changedFiles": files.get("count"),
        "addLines": files.get("totalAddLines"),
        "delLines": files.get("totalDelLines"),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"repo          {summary['repo']}")
    print(f"id            {summary['id']}")
    print(f"iid           {summary['iid']}")
    print(f"state         {summary['state']}")
    print(f"title         {summary['title']}")
    print(
        f"branch        {summary['sourceBranch']} -> {summary['targetBranch']}")
    print(f"mergeStatus   {summary['mergeStatus']}")
    print(f"changed       {summary['changedFiles']} files "
          f"(+{summary['addLines']} / -{summary['delLines']})")
    print(f"web           {summary['webUrl']}")
    if summary["id"] is None:
        print("WARN: 响应没有项目级 id；确认 --mr 是否误用了 iid")
    if summary["iid"] is None:
        print("WARN: 响应没有 iid；无法构造 MR 页面链接")
    return 0


def cmd_list(args, runner=None) -> int:
    runner = runner or mr_backend.run_tool
    repo = resolve_repo(args.repo, args.worktree)
    raw = fetch_comments(repo, args.mr, runner)
    worktree = worktree_state(args.worktree, repo)
    comments = [normalize_comment(item, worktree.get("head")) for item in raw]
    filtered = filter_comments(
        comments, state=args.state,
        severities=_parse_severities(args.severity),
        path=args.path, ids=_parse_ids(args.ids), limit=args.limit)
    if args.json:
        print(json.dumps({
            "repo": repo,
            "mergeRequestId": args.mr,
            "worktree": worktree,
            "total": len(comments),
            "matched": len(filtered),
            "all": _counts(comments),
            "counts": _counts(filtered),
            "comments": filtered,
        }, ensure_ascii=False, indent=2))
        return 0
    _print_list(repo, args.mr, comments, filtered, worktree,
                worktree.get("branch"))
    return 0


def cmd_show(args, runner=None) -> int:
    runner = runner or mr_backend.run_tool
    repo = resolve_repo(args.repo, args.worktree)
    raw = fetch_comments(repo, args.mr, runner)
    worktree = worktree_state(args.worktree, repo)
    comment = normalize_comment(find_comment(
        raw, args.id), worktree.get("head"))
    if args.json:
        print(json.dumps(comment, ensure_ascii=False, indent=2))
        return 0
    platform = comment["platform"]
    print(f"id          {comment['id']}")
    print(f"state       {comment['state']} / {comment['interpretation']} "
          f"(adopted={platform['adopted']}, closed={platform['closed']})")
    print(f"severity    {comment['category']} / {comment['severity']}")
    line = f":{comment['line']}" if comment.get("line") is not None else ""
    print(f"location    {comment['path']}{line}")
    print(f"outdated    {comment['outdated']}")
    print(
        f"context     {comment['old_sha'] or '-'} -> {comment['new_sha'] or '-'}")
    if comment["head_matches"] is not None:
        print(f"head        matches={comment['head_matches']}")
        if comment["head_matches"] is False:
            print(f"WARN: 评论 context 与当前 HEAD 不一致；当前 branch="
                  f"{worktree.get('branch') or '?'}，先确认代码版本。")
    print(f"author      {comment['author']}")
    if comment["kind"] in ("ignored", "closed"):
        print(f"\nNOTE: 平台已处置（{comment['interpretation']}，closed=1）。"
              "这只是流程动作，不代表误报 / 已修复，也不表示会重新打开。要在本地重新分析："
              "用 `review.py artifact --state all`（或 --include-closed）重新生成，纳入 active findings 后基于当前代码重判。")
    elif comment["state"] == "pending":
        print("\n下一步：正常本地分析（list → show → artifact → patch）。")
    print("\n## Note\n")
    print(comment["note"] or "(empty)")
    if comment["diff_context"]:
        print("\n## Diff context\n```diff")
        print(comment["diff_context"].rstrip())
        print("```")
    if comment["suggestion"]:
        print("\n## Suggestion\n```diff")
        print(str(comment["suggestion"].get("diff") or "").rstrip())
        print("```")
        print(f"applied={comment['suggestion'].get('applied')}")
    return 0


def validate_feedback(action: str, reason_code: str | None,
                      reason: str | None) -> None:
    if action not in ACTIONS:
        raise ReviewError(f"未知 action：{action}；可用：{', '.join(ACTIONS)}")
    if reason and len(reason) > 2000:
        raise ReviewError("--reason 过长（>2000 字符）；详细证据请用 reply")
    if action == "adopt":
        if reason_code:
            raise ReviewError("adopt 不支持 reason code；修复证据请用 reply 提交")
        return
    if reason_code and reason:
        raise ReviewError("--reason-code 与 --reason 二选一")
    if not reason_code and not reason:
        raise ReviewError(f"{action} 必须给出 --reason-code 或 --reason")
    if reason_code and reason_code not in REASON_CODES[action]:
        raise ReviewError(
            f"{action} 不支持 reason code {reason_code!r}；"
            f"可用：{', '.join(sorted(REASON_CODES[action]))}")


def _feedback_payload(args) -> dict:
    payload = {
        "repo": resolve_repo(args.repo, args.worktree),
        "mergeRequestId": args.mr,
        "noteId": args.id,
        "action": args.action,
    }
    if args.reason_code:
        payload["reason"] = args.reason_code
    elif args.reason:
        payload["reason"] = args.reason
    return payload


def cmd_feedback(args, runner=None) -> int:
    runner = runner or mr_backend.run_tool
    validate_feedback(args.action, args.reason_code, args.reason)
    payload = _feedback_payload(args)
    raw = fetch_comments(payload["repo"], args.mr, runner)
    comment = normalize_comment(find_comment(raw, args.id))
    if comment["parent_note_id"] is not None:
        raise ReviewError("该 note 是回复而不是顶层 AI 评论；不要对它提交 operate_ai_comment")
    if comment["state"] != "pending" and not args.include_handled:
        raise ReviewError(
            f"note {args.id} 已是 {comment['state']}；重新 list 确认，"
            "确需覆盖用 --include-handled")
    if comment["state"] != "pending" and args.include_handled:
        print(f"WARN: note {args.id} 已是 {comment['state']}；"
              "按 --include-handled 显式覆盖。", file=sys.stderr)
    if not args.confirm:
        _print_dry_run("operate_ai_comment", payload, args.json)
        return 0
    result = runner("operate_ai_comment", payload, retry=False)
    _print_write_result("operate_ai_comment", payload, result, args.json)
    return 0


def _read_note(args) -> str:
    if bool(args.note) == bool(args.note_file):
        raise ReviewError("--note 与 --note-file 必须二选一")
    if args.note_file:
        path = Path(args.note_file)
        if not path.is_file():
            raise ReviewError(f"找不到 --note-file：{path}")
        note = path.read_text(encoding="utf-8")
    else:
        note = args.note
    if not note.strip():
        raise ReviewError("回复内容为空")
    return note


def cmd_reply(args, runner=None) -> int:
    runner = runner or mr_backend.run_tool
    note = _read_note(args)
    repo = resolve_repo(args.repo, args.worktree)
    raw = fetch_comments(repo, args.mr, runner)
    target = find_comment(raw, args.id)
    if target.get("parentNoteId") is not None:
        raise ReviewError("只能回复顶层评论；该 note 已经是回复")
    payload = {
        "repo": repo,
        "mergeRequestId": args.mr,
        "note": note,
        "parentNoteId": args.id,
    }
    if not args.confirm:
        _print_dry_run("comment_merge_request", payload, args.json)
        return 0
    result = runner("comment_merge_request", payload, retry=False)
    _print_write_result("comment_merge_request", payload, result, args.json)
    return 0


def cmd_artifact(args, runner=None) -> int:
    from review_artifact import cmd_artifact as _cmd_artifact
    return _cmd_artifact(args, runner=runner)


def _load_json(path: str | Path, label: str) -> dict:
    target = Path(path)
    if not target.is_file():
        raise ReviewError(f"找不到 {label}：{target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReviewError(f"无法读取 {label}：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewError(f"{label} 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ReviewError(f"{label} 必须是 JSON 对象")
    return data


def _normalize_patch_path(path) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ReviewError("patch.set 的字段路径必须是非空字符串")
    text = path.strip()
    if text.startswith("analysis."):
        text = text[len("analysis."):]
    if text == "analysis":
        raise ReviewError("patch.set 的键相对 analysis；不要写 analysis 本身")
    root = text.split(".", 1)[0]
    if root in PATCH_FORBIDDEN_FIELDS:
        if root in ("decision", "status"):
            raise ReviewError(
                f"{path} 是人工决策字段，不在 review.json 中；"
                "请在 review.html 中决策，不要用 patch 修改")
        if root == "note":
            raise ReviewError(
                "note 不是 analysis 字段；说明请写 trigger / impact / "
                "rootCause / proposal.summary")
        raise ReviewError(f"{path} 不允许由 patch 修改")
    if root not in ANALYSIS_FIELDS:
        raise ReviewError(
            f"未知 analysis 字段 {root!r}；可用：{', '.join(sorted(ANALYSIS_FIELDS))}")
    if root == "proposal" and "." in text:
        subfield = text.split(".", 1)[1].split(".", 1)[0]
        if subfield not in PROPOSAL_FIELDS:
            raise ReviewError(
                f"未知 proposal 字段 {subfield!r}；"
                f"可用：{', '.join(sorted(PROPOSAL_FIELDS))}")
    if root in ("evidence", "openQuestions") and "." in text:
        raise ReviewError(
            f"{path} 是数组字段，请整体替换，不要用点路径逐项修改")
    return text


def _patch_set(container: dict, path: str, value) -> None:
    parts = path.split(".")
    current = container
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
            current[part] = child
        elif not isinstance(child, dict):
            raise ReviewError(f"patch 字段路径冲突：{path}")
        current = child
    current[parts[-1]] = value


def cmd_patch(args) -> int:
    import review_contract
    artifact_path = Path(args.artifact)
    raw_patch_paths = args.patch if isinstance(
        args.patch, list) else [args.patch]
    patch_paths = [Path(path) for path in raw_patch_paths if path]
    if not patch_paths:
        raise ReviewError("至少需要一个 --patch")
    artifact = _load_json(artifact_path, "artifact")
    merged_items = []
    for patch_path in patch_paths:
        patch = _load_json(patch_path, "patch")
        if patch.get("schemaVersion") != review_contract.SCHEMA_VERSION:
            raise ReviewError(
                f"patch.schemaVersion 必须是 {review_contract.SCHEMA_VERSION}")
        if patch.get("reviewKey") != artifact.get("reviewKey"):
            raise ReviewError(f"{patch_path}: reviewKey 与 artifact 不一致")
        items = patch.get("findings")
        if not isinstance(items, list) or not items:
            raise ReviewError(f"{patch_path}: patch.findings 必须是非空数组")
        merged_items.extend(items)

    findings = artifact.get("findings")
    if not isinstance(findings, list):
        raise ReviewError("artifact.findings 必须是数组")
    by_id = {finding.get("id"): finding for finding in findings
             if isinstance(finding, dict)}
    touched = []
    seen = set()
    for index, item in enumerate(merged_items):
        prefix = f"patch.findings[{index}]"
        if not isinstance(item, dict):
            raise ReviewError(f"{prefix} 必须是对象")
        finding_id = item.get("id")
        if not isinstance(finding_id, int) or isinstance(finding_id, bool):
            raise ReviewError(f"{prefix}.id 必须是整数")
        if finding_id in seen:
            raise ReviewError(f"{prefix}.id 跨 patch 重复：{finding_id}")
        seen.add(finding_id)
        finding = by_id.get(finding_id)
        if not isinstance(finding, dict):
            raise ReviewError(f"{prefix}.id {finding_id} 不在 artifact 中")
        changes = item.get("set")
        if not isinstance(changes, dict) or not changes:
            raise ReviewError(f"{prefix}.set 必须是非空对象")
        analysis = finding.get("analysis")
        if analysis is None:
            analysis = {}
            finding["analysis"] = analysis
        elif not isinstance(analysis, dict):
            raise ReviewError(
                f"{prefix}.id {finding_id} 的 analysis 不是对象；"
                "先用 patch 设置完整 analysis")
        for raw_path, value in changes.items():
            path = _normalize_patch_path(raw_path)
            _patch_set(analysis, path, value)
        finding["proposalFingerprint"] = (
            review_contract.compute_proposal_fingerprint(finding))
        touched.append(finding)

    if args.allow_incomplete:
        saved = [(finding, finding.get("analysis")) for finding in findings
                 if isinstance(finding, dict)]
        for finding, _analysis in saved:
            finding["analysis"] = None
        errors = review_contract.validate_review_artifact(
            artifact, require_analysis=False)
        for finding, analysis in saved:
            finding["analysis"] = analysis
    else:
        errors = review_contract.validate_review_artifact(
            artifact, require_analysis=False)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    updated = ", ".join(str(finding["id"]) for finding in touched)
    print(f"patch={', '.join(str(path) for path in patch_paths)}  "
          f"reviewKey={artifact['reviewKey']}")
    print(f"updated={len(touched)}  {updated}")
    if args.allow_incomplete:
        print("WARN: 允许部分 analysis；review_html 仍会拒绝不完整的 artifact。")
    if args.dry_run:
        print("未写入。")
        return 0
    text = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
    temporary = artifact_path.with_name(artifact_path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(artifact_path)
    print(f"written={artifact_path}")
    return 0


def cmd_check_envelope(args) -> int:
    import review_contract
    artifact = _load_json(args.artifact, "artifact")
    envelope = _load_json(args.envelope, "Decision Envelope")
    artifact_errors = review_contract.validate_review_artifact(
        artifact, require_analysis=True)
    if artifact_errors:
        for error in artifact_errors:
            print(f"ERROR: artifact: {error}", file=sys.stderr)
        return 1
    errors, authorized, stale, invalid = (
        review_contract.validate_decision_envelope(envelope, artifact))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    by_id = {finding["id"]: finding for finding in artifact["findings"]}
    statuses = Counter(
        decision.get("status", "MISSING") for decision in envelope["decisions"])
    print(f"reviewKey={envelope['reviewKey']}")
    print(f"decisions={len(envelope['decisions'])}  "
          f"authorized={len(authorized)}  stale={len(stale)}  "
          f"invalid={len(invalid)}  "
          + "  ".join(f"{key}={value}" for key, value in sorted(statuses.items())))
    for finding_id in authorized:
        finding = by_id[finding_id]
        status = next(decision["status"] for decision in envelope["decisions"]
                      if decision["findingId"] == finding_id)
        print(
            f"  AUTHORIZED  {finding_id}  {status}  {finding['source']['path']}")
    for item in stale:
        print(f"  STALE       {item['findingId']}  {item['reason']}")
    for item in invalid:
        print(f"  INVALID     {item['findingId']}  {item['reason']}")
    if stale or invalid:
        print("PARTIAL: 只执行 AUTHORIZED 项；STALE / INVALID 项需重新决策。")
        return 0
    print("OK: Decision Envelope 与 artifact 一致；只执行 authorized 项。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Code Review 的 artifact、读取与平台反馈脚本（默认 dry-run）")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo", help="仓库路径，如 acme/webapp；缺省从 origin 推断")
    common.add_argument(
        "--mr", type=int, required=True,
        help="MR 的项目级 id（不是 iid）")
    common.add_argument(
        "--worktree", default=".",
        help="本地 worktree，用于 HEAD 对比；默认当前目录")
    sub = parser.add_subparsers(dest="command", required=True)

    mr_parser = sub.add_parser("mr", parents=[common], help="MR 基本信息")
    mr_parser.add_argument("--json", action="store_true")
    mr_parser.set_defaults(func=cmd_mr)

    list_parser = sub.add_parser("list", parents=[common], help="列出 AI 评论")
    list_parser.add_argument("--state",
                             choices=("pending", "handled",
                                      "ignored", "closed", "all"),
                             default="pending")
    list_parser.add_argument("--severity", help="high,medium,low")
    list_parser.add_argument("--path", help="路径子串")
    list_parser.add_argument("--ids", help="逗号分隔的 note id")
    list_parser.add_argument("--limit", type=int)
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(func=cmd_list)

    show_parser = sub.add_parser("show", parents=[common], help="查看单条 finding")
    show_parser.add_argument("--id", type=int, required=True, dest="id")
    show_parser.add_argument("--json", action="store_true")
    show_parser.set_defaults(func=cmd_show)

    artifact_parser = sub.add_parser(
        "artifact", parents=[common], help="生成 review.json 骨架")
    artifact_parser.add_argument(
        "--out", help="输出路径；默认 .engineering/work/ai-review/...")
    artifact_parser.add_argument("--ids", help="只生成指定 note id（逗号分隔），用于试点")
    artifact_parser.add_argument(
        "--include-closed", action="store_true",
        help="把平台上已关闭的评论也纳入 active findings（等价 --state all）")
    artifact_parser.add_argument(
        "--state", default="pending",
        choices=("pending", "handled", "ignored", "closed", "all"),
        help="纳入可分析 active findings 的平台状态；all 含已忽略 / 已处理，便于重分析")
    artifact_parser.add_argument(
        "--force", action="store_true",
        help="显式允许覆盖已有分析；默认拒绝静默覆盖")
    artifact_parser.set_defaults(func=cmd_artifact)

    feedback_parser = sub.add_parser(
        "feedback", parents=[common], help="提交 adopt / ignore / reject")
    feedback_parser.add_argument("--id", type=int, required=True, dest="id")
    feedback_parser.add_argument("--action", choices=ACTIONS, required=True)
    feedback_parser.add_argument("--reason-code")
    feedback_parser.add_argument("--reason")
    feedback_parser.add_argument("--confirm", action="store_true")
    feedback_parser.add_argument("--include-handled", action="store_true",
                                 help="显式允许覆盖已 handled 的评论")
    feedback_parser.add_argument("--json", action="store_true")
    feedback_parser.set_defaults(func=cmd_feedback)

    reply_parser = sub.add_parser(
        "reply", parents=[common], help="回复 AI 评论")
    reply_parser.add_argument("--id", type=int, required=True, dest="id")
    reply_parser.add_argument("--note")
    reply_parser.add_argument("--note-file")
    reply_parser.add_argument("--confirm", action="store_true")
    reply_parser.add_argument("--json", action="store_true")
    reply_parser.set_defaults(func=cmd_reply)

    patch_parser = sub.add_parser(
        "patch", help="按字段批量更新 review.json 的 analysis")
    patch_parser.add_argument("--artifact", required=True)
    patch_parser.add_argument(
        "--patch", required=True, action="append",
        help="patch 文件；可重复，用于合并并行 worker 的片段")
    patch_parser.add_argument("--allow-incomplete", action="store_true",
                              help="允许只写部分字段；review_html 仍要求完整")
    patch_parser.add_argument("--dry-run", action="store_true")
    patch_parser.set_defaults(func=cmd_patch)

    check_parser = sub.add_parser(
        "check-envelope",
        help="逐条校验授权：输出 AUTHORIZED / STALE / INVALID，不因单条失败阻断全部")
    check_parser.add_argument("--artifact", required=True)
    check_parser.add_argument("--envelope", required=True)
    check_parser.set_defaults(func=cmd_check_envelope)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ReviewError, mr_backend.PlatformError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
