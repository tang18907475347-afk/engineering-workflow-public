#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从平台数据生成 review.json 骨架。

active finding 保留空分析槽位；平台已关闭项放入 closedFindings，只汇报、不分析。
finding 是否成立、根因和修复方案由 Agent 填写。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import review
import review_contract


def _unique_review_head(comments: list[dict]) -> str | None:
    shas = {comment["new_sha"] for comment in comments if comment.get("new_sha")}
    return next(iter(shas)) if len(shas) == 1 else None


def _head_matches(comments: list[dict]) -> bool | None:
    known = [comment["head_matches"] for comment in comments
             if comment.get("head_matches") is not None]
    if not known:
        return None
    return all(known)


def _platform_counts(comments: list[dict]) -> dict:
    states = Counter(comment["state"] for comment in comments)
    interpretations = Counter(
        review_contract.platform_interpretation(
            comment["platform"].get("adopted"),
            comment["platform"].get("closed"))
        for comment in comments)
    return {
        "states": dict(sorted(states.items())),
        "interpretations": dict(sorted(interpretations.items())),
    }


def _state_active(comment: dict, state: str) -> bool:
    """哪些平台状态的评论纳入可分析 active findings。

    默认只分析 pending；`all` 覆盖任意状态，使“重分析已忽略 / 已合并”
    成为正路而非特殊 flag。判据统一用 state / kind，不再用 `closed == 1`。
    """
    if state == "all":
        return True
    if state in ("pending", "handled"):
        return comment["state"] == state
    return comment["kind"] == state


def default_artifact_path(worktree: str | Path, repo: str, mr_id: int,
                          head: str | None) -> Path:
    slug = f"{repo.replace('/', '__')}__{int(mr_id)}__{(head or 'unknown')[:8]}"
    return (Path(worktree) / ".engineering" / "work" / "ai-review"
            / slug / "review.json")


def _source_for(comment: dict) -> dict:
    return {
        "note": comment["note"],
        "category": comment["category"],
        "severity": comment["severity"],
        "severityLabel": comment["severity_label"],
        "title": comment["title"],
        "path": comment["path"],
        "line": comment["line"],
        "lineRange": comment["line_range"],
        "side": comment["side"],
        "context": comment["context"],
        "oldSha": comment["old_sha"],
        "newSha": comment["new_sha"],
        "headMatches": comment["head_matches"],
        "outdated": comment["outdated"],
        "platformState": comment["state"],
        "platform": comment["platform"],
        "platformInterpretation": review_contract.platform_interpretation(
            comment["platform"].get("adopted"),
            comment["platform"].get("closed")),
        "suggestion": comment["suggestion"],
        "diffContext": comment["diff_context"],
        "author": comment["author"],
        "createdAt": comment["created_at"],
        "updatedAt": comment["updated_at"],
    }


def build_artifact(repo: str, mr_id: int, detail: dict,
                   raw_comments: list[dict], worktree: str | Path,
                   artifact_path: str | Path | None = None,
                   include_closed: bool = False,
                   state: str = "pending",
                   requested_ids: list[int] | None = None) -> dict:
    head = review.git_head(worktree)
    status = review.git_status(worktree)
    branch = review.git_branch(worktree)
    dirty_files = [line[3:] for line in (status or "").splitlines()[:10]]
    comments = [review.normalize_comment(item, head) for item in raw_comments]
    iid = detail.get("iid")
    path = Path(artifact_path) if artifact_path else default_artifact_path(
        worktree, repo, mr_id, head)
    path = path.resolve()
    effective_state = "all" if include_closed else state
    active_comments = [c for c in comments if _state_active(c, effective_state)]
    closed_comments = [c for c in comments
                       if not _state_active(c, effective_state)]
    findings = [
        {
            "id": comment["id"],
            "proposalFingerprint": None,
            "source": _source_for(comment),
            "analysis": None,
        }
        for comment in active_comments
    ]
    closed_findings = [
        {
            "id": comment["id"],
            "source": _source_for(comment),
        }
        for comment in closed_comments
    ]

    return {
        "schemaVersion": review_contract.SCHEMA_VERSION,
        "reviewKey": review_contract.compute_review_key(repo, mr_id),
        "artifactPath": str(path),
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "repo": repo,
        "mergeRequestId": int(mr_id),
        "iid": iid,
        "mrUrl": review.mr_web_url(
            repo, iid, worktree, base_url=detail.get("webUrl")),
        "sourceBranch": detail.get("sourceBranch"),
        "targetBranch": detail.get("targetBranch"),
        "reviewHead": _unique_review_head(comments),
        "worktreeHead": head,
        "headMatches": _head_matches(comments),
        "selection": {
            "mode": "ids" if requested_ids else "all",
            "requestedIds": sorted(requested_ids) if requested_ids else [],
        },
        "preflight": {
            "repo": repo,
            "id": int(mr_id),
            "iid": iid,
            "worktree": str(Path(worktree).resolve()),
            "sourceBranch": detail.get("sourceBranch"),
            "targetBranch": detail.get("targetBranch"),
            "head": head,
            "branch": branch,
            "branchMatchesSource": (
                None if not branch or not detail.get("sourceBranch")
                else branch == detail.get("sourceBranch")),
            "dirty": None if status is None else bool(status),
            "dirtyFiles": dirty_files,
        },
        "summary": {
            "total": len(comments),
            "active": len(findings),
            "closed": len(closed_findings),
            "platform": _platform_counts(comments),
        },
        "findings": findings,
        "closedFindings": closed_findings,
    }


def _has_existing_analysis(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        return True
    return any(isinstance(finding, dict) and finding.get("analysis") is not None
               for finding in findings)


def cmd_artifact(args, runner=None) -> int:
    runner = runner or review.client.run_tool
    repo = review.resolve_repo(args.repo, args.worktree)
    detail = runner("get_merge_request_detail",
                    {"repo": repo, "mergeRequestId": args.mr})
    raw_comments = review.fetch_comments(repo, args.mr, runner)
    ids = review._parse_ids(getattr(args, "ids", None))
    if ids:
        raw_comments = [comment for comment in raw_comments
                        if comment.get("id") in ids]
        if not raw_comments:
            raise review.ReviewError(
                "--ids 没有匹配当前 MR 的 AI 评论；未生成 artifact")
    if not raw_comments:
        raise review.ReviewError("当前 MR 没有 AI 评论；未生成 artifact")
    if not isinstance(detail, dict):
        detail = {}
    include_closed = bool(getattr(args, "include_closed", False))
    state = getattr(args, "state", "pending")
    path = Path(args.out) if args.out else default_artifact_path(
        args.worktree, repo, args.mr, review.git_head(args.worktree))
    if (_has_existing_analysis(path)
            and not bool(getattr(args, "force", False))):
        raise review.ReviewError(
            f"目标 artifact 已包含分析，拒绝覆盖以保护已有知识：{path}；"
            "请用 --out 生成新文件，或显式 --force 丢弃旧分析")
    artifact = build_artifact(
        repo, args.mr, detail, raw_comments, args.worktree,
        artifact_path=path, include_closed=include_closed,
        state=state, requested_ids=ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

    active = len(artifact["findings"])
    closed = len(artifact["closedFindings"])
    print(f"artifact={path}")
    print(f"reviewKey={artifact['reviewKey']}")
    print(f"total={artifact['summary']['total']}  active={active}  closed={closed}  "
          f"headMatches={artifact['headMatches']}")
    if ids:
        print(f"NOTE: 试点子集，只包含 {len(ids)} 个指定 note id；"
              "不是该 MR 的全部 AI 评论。")
    if artifact["headMatches"] is False:
        print("WARN: 评论 context 与当前 HEAD 不一致；填写分析前先确认代码版本，"
              "执行前还要核对证据是否仍适用。")
    handled = artifact["summary"]["platform"]["states"].get("handled", 0)
    if handled == artifact["summary"]["total"] and handled:
        print("NOTE: 全部评论已是 handled；不要把 closed 当成已修复。")
    if closed:
        print(f"NOTE: {closed} 条本次不纳入分析（默认只分析 pending；其余只读汇报）；"
              "要重分析已忽略 / 已处理时加 --state all（或 --include-closed 别名）。")
    not_adopted = artifact["summary"]["platform"]["interpretations"].get(
        "CLOSED_NOT_ADOPTED", 0)
    if not_adopted:
        print(f"NOTE: {not_adopted} 条评论是 CLOSED_NOT_ADOPTED"
              "（已关闭但未采纳）；不等于已修复，也不等于误报。")
    if active:
        print("下一步：用 review.py patch 批量填写 analysis，再运行 review_html.py。")
    else:
        print("没有 active finding；可直接运行 review_html.py 查看已关闭汇报。")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成 review.json 骨架")
    parser.add_argument("--repo", help="foo/bar；缺省从 origin 推断")
    parser.add_argument("--mr", type=int, required=True,
                        help="MR 的项目级 id（不是 iid）")
    parser.add_argument("--worktree", default=".")
    parser.add_argument("--out", help="输出路径；默认 .engineering/work/ai-review/.../review.json")
    parser.add_argument(
        "--include-closed", action="store_true",
        help="已处理（含 --state all 别名）：把已忽略 / 已关闭评论也纳入可分析 active findings")
    parser.add_argument(
        "--state", default="pending",
        choices=("pending", "handled", "ignored", "closed", "all"),
        help="纳入可分析 active findings 的平台状态；all 含已忽略 / 已处理，便于重分析")
    args = parser.parse_args(argv)
    try:
        return cmd_artifact(args)
    except (review.ReviewError, review.client.QpError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
