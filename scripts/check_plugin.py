#!/usr/bin/env python3
"""check_plugin.py — 校验 Agent Plugin / Skill 结构。

参考：Qoder（.qoder-plugin/plugin.json）、OpenAI Codex 插件（.codex-plugin/plugin.json）
与 SKILL.md 开放标准（YAML frontmatter 必填 name/description；name 必须与目录同名、
仅小写字母/数字/连字符；子目录约定 scripts/ references/ assets/ agents/ tests/）。

两层共享协议模型下的职责：
- Runtime locality：SKILL.md 引用的运行时资源必须存在于 <skill-root>/<relative-path>，
  禁止 ../ 跨目录引用，禁止 Plugin 根 fallback 掩盖失效引用；
- Shared copy consistency：带生成头的 skill-local references 副本必须与 shared/ 编辑源
  逐内容一致，drift 时报 ERROR 并提示运行 sync_shared_references.py，不自动修复。

只做机器可可靠判定的**结构**校验，不评价 skill 语义质量或触发准确度（那需要真实 prompt eval）。
所有问题批量收集后一次性输出。

用法:
  check_plugin.py [plugin-root] [--json] [--strict]
  默认 plugin-root = 本脚本上级目录（即插件根）。
退出码: 0=PASS, 1=存在 ERROR（或 --strict 下存在 WARN）, 2=用法/前置错误。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:  # PyYAML 可选：存在则做权威严格解析
    import yaml
    HAVE_YAML = True
except Exception:  # pragma: no cover
    yaml = None
    HAVE_YAML = False

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+].*)?$")
# SKILL.md 正文里指向 progressive-disclosure 资源的相对路径（含 shared/ 以便拦截误用）
RESOURCE_RE = re.compile(
    r"(?:\.\./)*(?:references|assets|scripts|shared|agents)/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+")
# shared 生成副本的头（Markdown 注释），由 sync_shared_references.py 产出
GENERATED_PATTERN = re.compile(
    r"^<!-- Generated from shared/(\S+) by scripts/sync_shared_references\.py\. Do not edit this copy directly\. -->$")
RUNTIME_AREA = "references"
KNOWN_SKILL_DIRS = {"scripts", "references", "assets", "agents", "tests"}
KNOWN_FRONTMATTER_KEYS = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "allowed-tools", "context", "model", "effort", "disable-model-invocation",
    "hooks", "license", "metadata",
}
YAML_INDICATORS = set("&*!#%@`|>\"'[],{}")
DESC_HARD_LIMIT = 1024   # 部分宿主对 description 的硬上限
DESC_SOFT_LIMIT = 500    # 超过则 Codex 初始清单可能截断，建议前置触发词


class Report:
    """批量收集问题，统一输出。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, scope: str, msg: str) -> None:
        self.errors.append(f"[{scope}] {msg}")

    def warn(self, scope: str, msg: str) -> None:
        self.warnings.append(f"[{scope}] {msg}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return ""


def _exists(path: Path) -> bool:
    try:
        return path.resolve().is_file()
    except OSError:
        return False


# ---------------- frontmatter ----------------

def split_frontmatter(text: str):
    """返回 (frontmatter_text, body, error)。"""
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "文件未以独立的 --- 开头（缺少 YAML frontmatter）"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:]), None
    return None, text, "缺少闭合的 --- frontmatter 分隔符"


def parse_frontmatter(fm: str, scope: str, report: Report):
    if HAVE_YAML:
        try:
            data = yaml.safe_load(fm)
        except Exception as exc:  # noqa: BLE001
            first = str(exc).splitlines()[0] if str(
                exc) else exc.__class__.__name__
            report.error(scope, f"YAML frontmatter 解析失败：{first}")
            return None
        if not isinstance(data, dict):
            report.error(scope, "frontmatter 不是键值映射")
            return None
        return data
    # 无 PyYAML：轻量解析，并主动探测会破坏 YAML 的写法
    data: dict[str, str] = {}
    for raw in fm.splitlines():
        if not raw.strip() or raw[:1] in (" ", "\t"):  # 跳过空行与缩进(块内容)
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        quoted = val[:1] in ('"', "'")
        if not quoted and ": " in val:
            report.error(scope, f"字段 {key} 的值含未加引号的 ': '，会破坏 YAML 解析（加引号或改写）")
        if not quoted and val[:1] in YAML_INDICATORS:
            report.warn(
                scope, f"字段 {key} 的值以 YAML 指示符 {val[:1]!r} 开头且未加引号，可能被误解析")
        data[key] = val
    return data


# ---------------- refs ----------------

def check_refs(skill_dir: Path, body: str, report: Report, scope: str) -> None:
    """Runtime locality：运行时资源必须 skill-local 可达，禁止跨目录与 Plugin 根回退。"""
    for tok in sorted(set(RESOURCE_RE.findall(body))):
        if tok.startswith("../") or "/../" in tok:
            report.error(scope, f"禁止跨目录资源引用（运行时依赖其他目录，不可移植）：{tok}")
            continue
        if tok.split("/", 1)[0] == "shared":
            report.error(
                scope, f"运行时不得依赖 shared/ 编辑源，应引用 skill-local 副本：{tok}")
            continue
        if not _exists(skill_dir / tok):
            report.error(
                scope, f"正文引用的资源在 skill 目录内不存在（违反 runtime locality）：{tok}")


def check_shared_copies(root: Path, skills_dir: Path, report: Report) -> None:
    """Shared copy consistency：去生成头后的副本必须与 shared/ 编辑源内容完全一致。"""
    shared_dir = root / "shared"
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        adir = d / RUNTIME_AREA
        if not adir.is_dir():
            continue
        for f in sorted(p for p in adir.iterdir() if p.is_file()):
            text = read_text(f).replace("\r\n", "\n")
            first, sep, rest = text.partition("\n")
            hit = GENERATED_PATTERN.match(first)
            if not hit:
                continue  # 非生成副本（skill 专属文件）不在此检查范围
            src, rel = shared_dir / hit.group(1), f.relative_to(root)
            if not sep or not src.is_file():
                report.error(
                    "shared-copy", f"{rel} 的生成头指向不存在的编辑源：shared/{hit.group(1)}")
                continue
            if rest != read_text(src).replace("\r\n", "\n"):
                report.error("shared-copy", f"{rel} 与 shared/{src.name} 不一致（silent drift）；"
                             f"请编辑 shared/ 源后运行 scripts/sync_shared_references.py")


# ---------------- skill ----------------

def check_skill(root: Path, d: Path, report: Report, seen: set[str]) -> None:
    scope = f"skill:{d.name}"
    skill_md = d / "SKILL.md"
    if not skill_md.is_file():
        report.error(scope, "缺少 SKILL.md")
        return
    fm, body, err = split_frontmatter(read_text(skill_md))
    if err:
        report.error(scope, err)
        return
    if not body.strip():
        report.warn(scope, "frontmatter 之后没有正文指令")
    data = parse_frontmatter(fm, scope, report)
    check_refs(d, body, report, scope)
    for sub in sorted(d.iterdir()):
        if sub.is_dir() and sub.name not in KNOWN_SKILL_DIRS:
            report.warn(
                scope, f"含非约定子目录 '{sub.name}/'（约定：{sorted(KNOWN_SKILL_DIRS)}）")
    if data is None:
        return

    extra = [k for k in data if k not in KNOWN_FRONTMATTER_KEYS]
    if extra:
        report.warn(
            scope, f"含非通用 frontmatter 字段 {extra}（跨 agent 仅 name/description 通用）")

    name = str(data.get("name", "")).strip()
    desc = str(data.get("description", "")).strip()
    if not name:
        report.error(scope, "frontmatter 缺少 name")
    else:
        if name != d.name:
            report.error(
                scope, f"name '{name}' 与目录名 '{d.name}' 不一致（会导致 skill 无法加载）")
        if not NAME_RE.match(name):
            report.error(scope, f"name '{name}' 非法：只允许小写字母/数字/连字符")
        if name in seen:
            report.error(scope, f"name '{name}' 与其他 skill 重复（宿主不会合并）")
        seen.add(name)
    if not desc:
        report.error(scope, "frontmatter 缺少 description")
    elif len(desc) > DESC_HARD_LIMIT:
        report.error(
            scope, f"description 长度 {len(desc)} 超过硬上限 {DESC_HARD_LIMIT}")
    elif len(desc) > DESC_SOFT_LIMIT:
        report.warn(
            scope, f"description 偏长（{len(desc)} 字符）：Codex 初始清单会截断，建议前置关键触发词")


# ---------------- manifest ----------------

def _load_json(path: Path, label: str, report: Report):
    if not path.is_file():
        return None
    try:
        data = json.loads(read_text(path))
    except Exception as exc:  # noqa: BLE001
        report.error(label, f"JSON 解析失败：{exc}")
        return None
    if not isinstance(data, dict):
        report.error(label, "顶层不是 JSON 对象")
        return None
    return data


def check_manifests(root: Path, report: Report):
    root_mf = root / "plugin.json"
    codex_mf = root / ".codex-plugin" / "plugin.json"
    qoder_mf = root / ".qoder-plugin" / "plugin.json"
    if not root_mf.is_file() and not codex_mf.is_file() and not qoder_mf.is_file():
        report.error(
            "manifest", "缺少 plugin.json、.codex-plugin/plugin.json 或 .qoder-plugin/plugin.json（至少需一个插件清单）")
        return root / "skills" if (root / "skills").is_dir() else None

    data_root = _load_json(root_mf, "plugin.json", report)
    data_codex = _load_json(codex_mf, ".codex-plugin/plugin.json", report)
    data_qoder = _load_json(qoder_mf, ".qoder-plugin/plugin.json", report)
    specs = (
        ("plugin.json", data_root, {"name", "version", "description"}),
        (".codex-plugin/plugin.json", data_codex,
         {"name", "version", "description", "skills"}),
        (".qoder-plugin/plugin.json", data_qoder,
         {"name", "version", "description", "skills"}),
    )
    for label, data, required in specs:
        if data is None:
            continue
        for k in sorted(required):
            v = data.get(k)
            if not (isinstance(v, str) and v.strip()):
                report.error(label, f"缺少必填字段或为空：{k}")
        name, ver = str(data.get("name", "")).strip(), str(
            data.get("version", "")).strip()
        if name and not NAME_RE.match(name):
            report.warn(label, f"name '{name}' 建议只用小写字母/数字/连字符")
        if ver and not SEMVER_RE.match(ver):
            report.warn(label, f"version '{ver}' 不是 semver(x.y.z)")

    present = [(label, data) for label, data in
               (("plugin.json", data_root),
                (".codex-plugin/plugin.json", data_codex),
                (".qoder-plugin/plugin.json", data_qoder)) if data]
    names = {str(data.get("name", "")).strip() for _label, data in present}
    versions = {str(data.get("version", "")).strip()
                for _label, data in present}
    if len(names) > 1:
        report.error("manifest", f"多个清单的 name 不一致：{sorted(names)}")
    if len(versions) > 1:
        report.error("manifest", f"多个清单的 version 不一致：{sorted(versions)}")
    descriptions = {str(data.get("description", "")).strip()
                    for _label, data in present}
    if len(descriptions) > 1:
        report.warn("manifest", "多个清单的 description 不一致")

    if data_root:
        nm = str(data_root.get("name", "")).strip()
        if nm and nm != root.name:
            report.warn("plugin.json",
                        f"name '{nm}' 与插件根目录名 '{root.name}' 不一致")

    skills_field = None
    for data in (data_qoder, data_codex, data_root):
        if data and isinstance(data.get("skills"), str):
            skills_field = data["skills"]
            break
    if skills_field:
        sd = (root / skills_field).resolve()
        if not sd.is_dir():
            report.error("manifest", f"清单 skills 路径无法解析为目录：{skills_field}")
            fallback = root / "skills"   # 仍回退扫描默认目录，避免掩盖 skill 级问题
            return fallback if fallback.is_dir() else None
        return sd
    default_sd = root / "skills"
    if not default_sd.is_dir():
        report.error("manifest", "未找到 skills/ 目录，且清单未指定 skills 路径")
        return None
    return default_sd


# ---------------- output ----------------

def emit(report: Report, json_out: bool, strict: bool, root: Path, skills: list[str]) -> int:
    failed = bool(report.errors) or (strict and bool(report.warnings))
    status = "FAIL" if failed else "PASS"
    if json_out:
        print(json.dumps({
            "status": status, "plugin": root.name, "skills": skills,
            "errors": report.errors, "warnings": report.warnings,
            "counts": {"errors": len(report.errors), "warnings": len(report.warnings)},
        }, ensure_ascii=False, indent=2))
        return 1 if failed else 0
    print(status)
    for e in report.errors:
        print(f"- ERROR: {e}")
    for w in report.warnings:
        print(f"- WARN: {w}")
    print(
        f"plugin={root.name} skills={len(skills)} | {len(report.errors)} ERROR, {len(report.warnings)} WARN")
    print("Structural Validation only：不评价 skill 语义质量 / 触发准确度（需真实 prompt eval）。")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    flags = {a for a in argv[1:] if a.startswith("--")}
    positional = [a for a in argv[1:] if not a.startswith("--")]
    unknown = flags - {"--json", "--strict"}
    if unknown:
        print(
            f"usage: check_plugin.py [plugin-root] [--json] [--strict]（未知参数：{sorted(unknown)}）")
        return 2
    root = Path(positional[0]).resolve() if positional else Path(
        __file__).resolve().parent.parent
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}")
        return 2

    report = Report()
    if not HAVE_YAML:
        report.warn("env", "未安装 PyYAML，使用内置启发式 frontmatter 解析（严格性略低）")

    skills_dir = check_manifests(root, report)
    seen: set[str] = set()
    if skills_dir and skills_dir.is_dir():
        subdirs = sorted(d for d in skills_dir.iterdir()
                         if d.is_dir() and not d.name.startswith("."))
        if not subdirs:
            report.error("skills", "skills/ 下没有任何 skill 目录")
        for d in subdirs:
            check_skill(root, d, report, seen)
        check_shared_copies(root, skills_dir, report)
    if not (root / "README.md").is_file():
        report.warn("plugin", "缺少根 README.md")

    return emit(report, "--json" in flags, "--strict" in flags, root, sorted(seen))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
