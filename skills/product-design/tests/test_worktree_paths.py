import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import worktree_paths as wp


def _git_init(tmp):
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
    return Path(tmp).resolve()


def test_engineering_root_is_worktree_scoped(tmp_path):
    root = _git_init(tmp_path)
    assert wp.engineering_root(root) == root / ".engineering"
    assert wp.requirement_source_dir("demo", "prd", root) == root / ".engineering/requirements/demo/sources/prd"
    assert wp.requirement_source_dir("demo", "design", root) == root / ".engineering/requirements/demo/sources/design"


def test_current_worktree_root(tmp_path):
    root = _git_init(tmp_path)
    sub = root / "a" / "b"
    sub.mkdir(parents=True)
    assert wp.current_worktree_root(sub) == root


def test_ensure_inside_rejects_escape(tmp_path):
    root = _git_init(tmp_path)
    data = root / ".engineering"
    data.mkdir()
    outside = root.parent / "evil.md"
    try:
        wp.ensure_inside(outside, data, "x")
        assert False, "should reject path outside data root"
    except wp.WorktreePathError:
        pass


def test_non_git_raises(tmp_path):
    sub = tmp_path / "nogit"
    sub.mkdir()
    with pytest.raises(wp.WorktreePathError):
        wp.current_worktree_root(sub)


def test_requirement_slug_rejects_parent_traversal(tmp_path):
    root = _git_init(tmp_path)
    with pytest.raises(wp.WorktreePathError):
        wp.requirement_source_dir("../other", "prd", root)


def test_requirement_source_rejects_symlink(tmp_path):
    root = _git_init(tmp_path)
    (root / ".engineering" / "requirements").mkdir(parents=True)
    (root / ".engineering" / "requirements" / "demo").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(wp.WorktreePathError):
        wp.requirement_source_dir("demo", "design", root)
