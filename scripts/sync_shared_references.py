#!/usr/bin/env python3
"""sync_shared_references.py — 把 shared/ 编辑源确定性复制为各 Skill 的 skill-local 运行时副本。

分层模型：
  Authoring SSOT:  shared/<name>.md                    —— 唯一编辑处
  Runtime copies:  skills/<skill>/references/<name>.md  —— 生成副本，禁止手改

行为（deterministic）：
- 只复制 DEPENDENCIES 中声明的依赖；
- 覆盖写入 generated copy（内容 = 生成头 + shared 源正文，逐字节确定）；
- 不修改不带生成头的 skill-local 专属文件；
- 删除依赖表已移除的孤儿生成副本（仅当首行匹配本工具生成头）；
- 不 commit / push，不做模板渲染，不做 schema migration。

用法:
  python3 scripts/sync_shared_references.py [plugin-root]
  默认 plugin-root = 本脚本上级目录（即插件根）。
退出码: 0=成功, 2=前置错误（shared 源缺失等）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# skill 名 -> 其运行时真正需要的 shared 文件名（没有 runtime dependency 就不打包）
DEPENDENCIES: dict[str, list[str]] = {
    "product-engineering": [
        "workspace-and-ownership.md", "evidence-and-correction.md",
        "delivery-and-handoff.md"],
    "product-reality": [
        "workspace-and-ownership.md", "evidence-and-correction.md",
        "delivery-and-handoff.md"],
    "product-design": [
        "workspace-and-ownership.md", "evidence-and-correction.md",
        "delivery-and-handoff.md"],
    "implementation-strategy": [
        "workspace-and-ownership.md", "evidence-and-correction.md",
        "delivery-and-handoff.md"],
    "test-readiness-review": [
        "workspace-and-ownership.md", "evidence-and-correction.md",
        "delivery-and-handoff.md"],
}

AREA = "references"
GENERATED_HEADER = ("<!-- Generated from shared/{name} by scripts/sync_shared_references.py. "
                    "Do not edit this copy directly. -->")
GENERATED_PATTERN = re.compile(
    r"^<!-- Generated from shared/(\S+) by scripts/sync_shared_references\.py\. "
    r"Do not edit this copy directly\. -->$"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def render(name: str, source: str) -> str:
    """生成副本 = 生成头 + shared 源正文（源本身以换行结尾，直接拼接）。"""
    return GENERATED_HEADER.format(name=name) + "\n" + source


def generated_src(path: Path) -> str | None:
    """首行是生成头则返回其指向的 shared 源文件名，否则 None。"""
    try:
        first = read_text(path).split("\n", 1)[0]
    except OSError:
        return None
    m = GENERATED_PATTERN.match(first)
    return m.group(1) if m else None


def sync(root: Path) -> int:
    shared_dir = root / "shared"
    skills_dir = root / "skills"
    if not shared_dir.is_dir() or not skills_dir.is_dir():
        print("ERROR: 缺少 shared/ 或 skills/ 目录")
        return 2

    missing = [n for names in DEPENDENCIES.values() for n in names
               if not (shared_dir / n).is_file()]
    if missing:
        print(f"ERROR: shared/ 缺少编辑源: {sorted(set(missing))}")
        return 2

    actions = 0
    for skill, names in sorted(DEPENDENCIES.items()):
        if not (skills_dir / skill / "SKILL.md").is_file():
            print(f"ERROR: skill 目录不存在或缺少 SKILL.md: skills/{skill}/")
            return 2
        desired = set(names)

        # 1) 正向同步：覆盖 generated copy
        for name in sorted(desired):
            target = skills_dir / skill / AREA / name
            content = render(name, read_text(shared_dir / name))
            if target.is_file() and read_text(target) == content:
                print(f"unchanged: skills/{skill}/{AREA}/{name}")
                continue
            existed = target.is_file()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
            print(
                f"{'updated' if existed else 'created '}: skills/{skill}/{AREA}/{name}")
            actions += 1

        # 2) 孤儿清理：带生成头但已不在依赖表中的副本（只删生成副本，绝不动专属文件）
        d = skills_dir / skill / AREA
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if not f.is_file():
                    continue
                src = generated_src(f)
                if src is not None and src not in desired:
                    f.unlink()
                    print(
                        f"removed : skills/{skill}/{AREA}/{f.name}（依赖已移除的生成副本）")
                    actions += 1

    print(f"sync done: {actions} change(s)")
    return 0


def main(argv: list[str]) -> int:
    positional = [a for a in argv[1:] if not a.startswith("--")]
    if len(positional) > 1:
        print("usage: sync_shared_references.py [plugin-root]")
        return 2
    root = Path(positional[0]).resolve() if positional else Path(
        __file__).resolve().parent.parent
    return sync(root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
