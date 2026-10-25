#!/usr/bin/env python3
"""check_plan.py — 检查 Workspace「验收与保持」与任务之间的覆盖关系。

只做机器可判定的检查，不判断验收项写得对不对：
- ERROR：plan.md 不存在；没有「验收与保持」一节；某个 AC / P 没有被任何任务覆盖；
         同一编号重复定义；任务引用了不存在的 AC / P。
- WARN ：缺少「给执行者」一节；某个任务没有关联任何 AC / P；AC 没写来源；
         P 既没引用 reality.md 的 PC-n，也没给出代码定位（文件#符号）。

所有问题一次性汇总输出（诊断型校验，不在第一个错误处停止）。

用法：python3 check_plan.py <workspace 目录或 plan.md 路径>
退出码：0 = 无 ERROR；1 = 存在 ERROR；2 = 用法错误或找不到 plan.md。
仅依赖 Python 3.9+ 标准库。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ID = r"(?:AC|P)-\d+"
ID_RE = re.compile(rf"(?<![A-Za-z0-9-])({ID})(?![0-9])")
DEF_RE = re.compile(rf"^\s*(?:[-*]\s*(?:\[[ xX]\]\s*)?|#{{2,5}}\s*)(?:~~)?\*{{0,2}}({ID})\b")
TASK_RE = re.compile(r"^\s*(?:#{2,5}\s*|[-*]\s*(?:\[[ xX]\]\s*)?)\*{0,2}(T-\d+)\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def section(text: str, title: str) -> str | None:
    """返回标题包含 title 的那一节正文（到同级或更高级标题为止）；没有则 None。"""
    out: list[str] = []
    level = None
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            if level is not None and len(m.group(1)) <= level:
                break
            if level is None and title in m.group(2):
                level = len(m.group(1))
                continue
        if level is not None:
            out.append(line)
    return "\n".join(out) if level is not None else None


def task_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current = None
    task_level = None
    for line in text.splitlines():
        m = TASK_RE.match(line)
        if m:
            current = m.group(1)
            h = HEADING_RE.match(line)
            task_level = len(h.group(1)) if h else None
            blocks[current] = blocks.get(current, "") + line + "\n"
            continue
        h = HEADING_RE.match(line)
        if current and h and (task_level is None or len(h.group(1)) <= task_level):
            current = None
            continue
        if current:
            blocks[current] += line + "\n"
    return blocks


def check(target: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    plan = target / "plan.md" if target.is_dir() else target
    if not plan.is_file():
        return [f"找不到 plan.md：{plan}"], []
    workspace = plan.parent
    plan_text = strip_comments(plan.read_text(encoding="utf-8"))

    if section(plan_text, "给执行者") is None:
        warns.append("plan.md 缺少「给执行者」一节（写代码的 Agent 可能不加载本 Skill，需要这节告诉它在哪里停、怎么记录）")

    acc = section(plan_text, "验收与保持")
    defs: dict[str, str] = {}
    if acc is None:
        errors.append("plan.md 缺少「验收与保持」一节")
    else:
        for line in acc.splitlines():
            m = DEF_RE.match(line)
            if not m:
                continue
            ident = m.group(1)
            if ident in defs:
                errors.append(f"{ident} 重复定义")
                continue
            defs[ident] = line
            struck = "~~" in line
            if struck:
                continue
            if ident.startswith("AC-") and "来源" not in line:
                warns.append(f"{ident} 没有写来源（已接受的决定、clarification 小节或用户的明确要求）")
            if ident.startswith("P-") and not re.search(r"PC-\d+|#\w", line):
                warns.append(f"{ident} 既没引用 reality.md 的 PC-n，也没给出代码定位（文件#符号）")
        if not defs:
            errors.append("「验收与保持」里没有任何 AC-n / P-n")

    texts = [plan_text]
    for phase in sorted(workspace.glob("phase-*.md")):
        texts.append(strip_comments(phase.read_text(encoding="utf-8")))
    blocks: dict[str, str] = {}
    for text in texts:
        for tid, block in task_blocks(text).items():
            blocks[tid] = blocks.get(tid, "") + block
    if not blocks:
        errors.append("没有找到任务（任务以 T-<n> 开头，标题或列表项均可，例如「- [ ] T-1 …」）")

    active = {i for i, line in defs.items() if "~~" not in line}
    covered: set[str] = set()
    for tid, block in sorted(blocks.items(), key=lambda kv: int(kv[0][2:])):
        refs = set(ID_RE.findall(block))
        if not refs:
            warns.append(f"{tid} 没有关联任何 AC / P（例如写「覆盖：AC-1、P-2」）")
        for r in sorted(refs - set(defs)):
            errors.append(f"{tid} 引用了不存在的 {r}")
        covered |= refs
    for ident in sorted(active - covered, key=lambda x: (x.split("-")[0], int(x.split("-")[1]))):
        errors.append(f"{ident} 没有被任何任务覆盖")
    return errors, warns


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_plan.py <workspace 目录或 plan.md 路径>")
        return 2
    target = Path(argv[1])
    errors, warns = check(target)
    if errors and errors[0].startswith("找不到 plan.md"):
        print(f"ERROR: {errors[0]}")
        return 2
    for e in errors:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARN:  {w}")
    print(f"{'FAIL' if errors else 'PASS'}：{len(errors)} ERROR，{len(warns)} WARN"
          "（只检查覆盖关系与格式，不判断内容是否正确）")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
