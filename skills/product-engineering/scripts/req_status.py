#!/usr/bin/env python3
"""req_status.py — 只读地列出各需求已有哪些产物与进度，供 Router 判断“继续推进”时的下一步。

只读文件、不写任何状态；进度全部从现有产物推出：
- clarification/ 是否有内容
- reality.md 是否存在、基于哪个 commit
- workspace/plan.md 是否存在、是否有「验收与保持」、任务完成数（- [x] T-n / - [ ] T-n）
- reviews/ 最近一份审查记录及其 Verdict，以及计划是否在那之后又改过

“参考下一步”只是提示，Router 仍按用户意图与 SKILL.md 判断，可以不采纳。

用法：python3 req_status.py [<requirement-slug>] [--root <项目根>]
退出码：0 正常；2 找不到 .engineering/ 或指定需求。
仅依赖 Python 3.9+ 标准库。
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

TASK_RE = re.compile(r"^\s*(?:#{2,5}\s*|[-*]\s*)(\[[ xX]\]\s*)?\*{0,2}(T-\d+)\b")


def find_root(explicit: str | None) -> Path | None:
    if explicit:
        root = Path(explicit).resolve()
        return root if (root / ".engineering").is_dir() else None
    here = Path.cwd().resolve()
    for d in (here, *here.parents):
        if (d / ".engineering").is_dir():
            return d
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
        if top and (Path(top) / ".engineering").is_dir():
            return Path(top)
    except (OSError, subprocess.CalledProcessError):
        pass
    return None


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def tasks(workspace: Path) -> tuple[int, int, bool]:
    """返回 (已完成, 总数, 是否有勾选框)。"""
    seen: dict[str, bool] = {}
    has_box = False
    for f in [workspace / "plan.md", *sorted(workspace.glob("phase-*.md"))]:
        for line in read(f).splitlines():
            m = TASK_RE.match(line)
            if not m:
                continue
            box = m.group(1)
            has_box = has_box or bool(box)
            done = bool(box) and box.strip()[1:2].lower() == "x"
            seen[m.group(2)] = seen.get(m.group(2), False) or done
    return sum(seen.values()), len(seen), has_box


def latest_review(req: Path) -> tuple[Path | None, str]:
    d = req / "reviews"
    files = sorted(d.glob("*.md")) if d.is_dir() else []
    if not files:
        return None, ""
    text = read(files[-1])
    m = re.search(r"\b(READY_FOR_TEST|BLOCK)\b", text)
    return files[-1], (m.group(1) if m else "未识别")


def describe(req: Path) -> list[str]:
    lines = [f"需求：{req.name}"]
    clar = req / "clarification"
    clar_files = sorted(p.name for p in clar.glob("*.md")) if clar.is_dir() else []
    lines.append(f"  澄清 clarification/：{'、'.join(clar_files) if clar_files else '无'}")
    reality = req / "reality.md"
    if reality.is_file():
        m = re.search(r"基于[:：]\s*`?([0-9a-f]{6,40})", read(reality))
        lines.append(f"  现状摘要 reality.md：有（基于 {m.group(1) if m else '未写 commit'}）")
    else:
        lines.append("  现状摘要 reality.md：无")
    ws = req / "workspace"
    plan = ws / "plan.md"
    if plan.is_file():
        text = read(plan)
        acc = "有" if re.search(r"^#{1,6}\s+.*验收与保持", text, re.M) else "无"
        done, total, has_box = tasks(ws)
        progress = f"{done}/{total}" if has_box else f"{total} 个任务（未使用勾选框，无法判断完成数）"
        lines.append(f"  实施计划 workspace/plan.md：有；「验收与保持」{acc}；任务 {progress}")
    else:
        done = total = 0
        has_box = False
        lines.append("  实施计划 workspace/plan.md：无")
    review, verdict = latest_review(req)
    if review:
        stale = plan.is_file() and plan.stat().st_mtime > review.stat().st_mtime + 1
        note = "；之后计划又有修改" if stale else ""
        lines.append(f"  最近审查 reviews/{review.name}：{verdict}{note}")
    else:
        lines.append("  最近审查：无")

    # 参考下一步（提示，不是指令）
    if not plan.is_file():
        hint = ("还没有实施计划：目标已明确 → implementation-strategy；"
                "目标或体验仍待决定 → product-design；只是小改动 → 直接实现")
    elif has_box and done < total:
        hint = f"计划进行中（{done}/{total}）：按 plan.md 的「给执行者」继续实现"
    elif review and verdict == "BLOCK":
        hint = "上一轮审查 BLOCK：在原实现上下文修复阻塞项后，在新上下文重新 test-readiness-review"
    elif review and verdict == "READY_FOR_TEST" and not (plan.is_file() and plan.stat().st_mtime > review.stat().st_mtime + 1):
        hint = "已 READY_FOR_TEST：交给 QA；提测后的缺陷 → bugfix；MR 上的 AI 评审意见 → ai-code-review"
    else:
        hint = "实现看起来已完成：在新上下文做 test-readiness-review"
    lines.append(f"  参考下一步：{hint}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="只读列出需求产物与进度")
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--root")
    args = ap.parse_args(argv)
    root = find_root(args.root)
    if root is None:
        print("找不到 .engineering/：还没有任何需求产物。")
        return 2
    reqs_dir = root / ".engineering" / "requirements"
    reqs = sorted(p for p in reqs_dir.iterdir() if p.is_dir()) if reqs_dir.is_dir() else []
    if args.slug:
        reqs = [p for p in reqs if p.name == args.slug]
        if not reqs:
            print(f"找不到需求 {args.slug}。")
            return 2
    if not reqs:
        print("还没有任何需求目录（.engineering/requirements/）。")
        return 0
    ctx = root / ".engineering" / "context.md"
    print(f"业务上下文 context.md：{'有' if ctx.is_file() else '无'}")
    for r in sorted(reqs, key=lambda p: max((f.stat().st_mtime for f in p.rglob('*') if f.is_file()), default=0), reverse=True):
        print("\n".join(describe(r)))
    print("（按最近修改排序；以上只读自现有产物，“参考下一步”仅供判断）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
