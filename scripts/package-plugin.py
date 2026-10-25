#!/usr/bin/env python3
"""Package the shared Product Engineering skills as a Qoder or Codex plugin ZIP.

The source repository remains the single source of truth. This script only
stages the selected manifest, shared skills, and repository documentation; it
does not generate or transform any Skill content.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import NoReturn


TARGETS = {
    "qoder": {
        "label": "Qoder",
        "manifest": Path(".qoder-plugin/plugin.json"),
        "output_dir": "qoder",
        "forbidden": (".git/", ".codex-plugin/", "dist/"),
    },
    "codex": {
        "label": "Codex",
        "manifest": Path(".codex-plugin/plugin.json"),
        "output_dir": "codex",
        "forbidden": (".git/", ".qoder-plugin/", "dist/"),
    },
}

EXCLUDED_DIRS = {
    ".git",
    ".codex-plugin",
    ".qoder-plugin",
    ".pytest_cache",
    ".plugin-eval",
    ".qoder",
    ".engineering",
    "__pycache__",
    "dist",
    ".idea",
    ".vscode",
}
EXCLUDED_FILES = {".DS_Store"}
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".tmp", ".swp", ".swo", "~")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=("qoder", "codex", "all"),
        default="all",
        help="plugin target to package (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="ZIP output path; only valid with a single --target",
    )
    return parser.parse_args(argv)


def fail(message: str) -> NoReturn:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_manifest(repo_root: Path, target: str) -> tuple[dict, Path]:
    label = TARGETS[target]["label"]
    manifest_path = repo_root / TARGETS[target]["manifest"]
    if not manifest_path.is_file():
        fail(f"missing {label} manifest: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read {label} manifest: {exc}")
    if not isinstance(manifest, dict):
        fail(f"{label} manifest must be a JSON object")
    for field in ("name", "version", "skills"):
        if not manifest.get(field):
            fail(f"{label} manifest is missing required packaging field: {field}")
    if not isinstance(manifest["name"], str) or not isinstance(manifest["version"], str):
        fail(f"{label} manifest name and version must be strings")
    if not isinstance(manifest["skills"], (str, list)):
        fail(f"{label} manifest skills must be a path string or list of paths")
    return manifest, manifest_path


def skill_paths(repo_root: Path, manifest: dict, target: str) -> list[Path]:
    label = TARGETS[target]["label"]
    declared = manifest["skills"]
    paths = [declared] if isinstance(declared, str) else declared
    resolved: list[Path] = []
    for path_value in paths:
        if not isinstance(path_value, str) or not path_value.startswith("./"):
            fail(f"{label} manifest skill path must start with './': {path_value!r}")
        path = (repo_root / path_value[2:]).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            fail(f"{label} manifest skill path escapes repository: {path_value}")
        if not path.is_dir():
            fail(f"{label} manifest skill path does not exist: {path_value}")
        resolved.append(path)
    return resolved


def copy_filter(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in EXCLUDED_DIRS
        or name in EXCLUDED_FILES
        or name.endswith(EXCLUDED_SUFFIXES)
    }


def stage_plugin(repo_root: Path, stage_root: Path, manifest: dict, target: str) -> None:
    manifest_rel = TARGETS[target]["manifest"]
    required_root_files = (manifest_rel, Path(
        "README.md"), Path("USER_PROMPTS.md"))
    for relative in required_root_files:
        source = repo_root / relative
        if not source.is_file():
            fail(f"required package file is missing: {relative}")
        destination = stage_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for skill_root in skill_paths(repo_root, manifest, target):
        relative = skill_root.relative_to(repo_root.resolve())
        destination = stage_root / relative
        shutil.copytree(skill_root, destination, ignore=copy_filter)

    # Plugin 根级共享 Tooling：随整包一起分发，保留共同 Plugin Root。
    # 依赖方向固定：Skill 专用 CLI → tools/*（确定性能力） → 外部服务；
    # 领域契约（如 review_contract）仍留在 Skill，不在此搬移。
    tools_root = repo_root / "tools"
    if tools_root.is_dir():
        shutil.copytree(tools_root, stage_root / "tools", ignore=copy_filter)

    skill_files = sorted((stage_root / "skills").glob("*/SKILL.md"))
    if not skill_files:
        fail("package contains no skills/*/SKILL.md files")


def zip_stage(stage_root: Path, output_path: Path, forbidden: tuple[str, ...]) -> list[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[str] = []
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(path for path in stage_root.rglob("*") if path.is_file()):
            relative = source.relative_to(stage_root).as_posix()
            if relative.startswith(forbidden):
                fail(f"excluded path leaked into staged package: {relative}")
            if relative.startswith("/") or ".." in Path(relative).parts:
                fail(f"unsafe ZIP entry: {relative}")
            archive.write(source, relative)
            entries.append(relative)
    return entries


def build_target(repo_root: Path, target: str, output_path: Path | None = None) -> list[str]:
    config = TARGETS[target]
    manifest, _manifest_path = load_manifest(repo_root, target)
    output_path = output_path or (
        repo_root / "dist" / config["output_dir"] /
        f"{manifest['name']}-{manifest['version']}.zip"
    )
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()

    with tempfile.TemporaryDirectory(prefix=f"product-engineering-{target}-") as temporary:
        stage_root = Path(temporary) / "plugin"
        stage_root.mkdir()
        stage_plugin(repo_root, stage_root, manifest, target)
        entries = zip_stage(stage_root, output_path, config["forbidden"])

    print(f"Created {output_path}")
    print(
        f"Entries: {len(entries)} files; skills: "
        f"{len(list((repo_root / 'skills').glob('*/SKILL.md')))}"
    )
    return entries


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    targets = tuple(TARGETS) if args.target == "all" else (args.target,)
    if args.output and len(targets) > 1:
        fail("--output can only be used with a single --target")

    for target in targets:
        build_target(repo_root, target, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
