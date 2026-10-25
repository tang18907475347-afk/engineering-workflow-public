#!/usr/bin/env python3
"""Keep requirement sources inside the active Git worktree's .engineering root."""

from __future__ import annotations

import subprocess
from pathlib import Path


class WorktreePathError(ValueError):
    """A runtime path does not belong to the active worktree or requirement."""


def current_worktree_root(cwd: Path | str | None = None) -> Path:
    location = Path(cwd or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(location), "rev-parse", "--show-toplevel"],
            text=True, capture_output=True, check=False,
        )
    except OSError as exc:
        raise WorktreePathError(f"无法定位当前 Git worktree：{exc}") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise WorktreePathError(f"当前目录不属于 Git worktree：{result.stderr.strip() or 'not a Git worktree'}")
    return Path(result.stdout.strip()).resolve()


def engineering_root(worktree_root: Path | str | None = None) -> Path:
    root = Path(worktree_root).resolve() if worktree_root is not None else current_worktree_root()
    candidate = root / ".engineering"
    if candidate.is_symlink():
        raise WorktreePathError(f"当前 worktree 的 .engineering 不能是 symlink：{candidate}")
    return candidate


def valid_req_slug(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and "/" not in value and "\\" not in value


def requirement_source_dir(req: str, kind: str, worktree_root: Path | str | None = None) -> Path:
    if not valid_req_slug(req):
        raise WorktreePathError("需求 slug 必须是单层目录名")
    if kind not in {"prd", "design", "attachments"}:
        raise WorktreePathError(f"未知来源类型：{kind}")
    base = engineering_root(worktree_root)
    path = base
    for segment in ("requirements", req, "sources", kind):
        path = path / segment
        if path.is_symlink():
            raise WorktreePathError(f"来源目录不能经过 symlink：{path}")
    return path


def ensure_inside(path: Path | str, root: Path | str, label: str) -> Path:
    root_path = Path(root).resolve()
    raw = Path(path).expanduser()
    candidate = raw if raw.is_absolute() else Path.cwd() / raw
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root_path)
    except (OSError, RuntimeError, ValueError) as exc:
        raise WorktreePathError(f"{label} 越出目标目录：{candidate}") from exc
    return resolved
