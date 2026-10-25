"""req_status.py 的单元测试（unittest）。

运行：python3 -m unittest discover -s skills/product-engineering/tests -v
"""
import contextlib
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import req_status  # noqa: E402


def make(files: dict) -> Path:
    root = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        p = root / ".engineering" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def run(root: Path, *args: str):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = req_status.main(["--root", str(root), *args])
    return code, buf.getvalue()


PLAN = "## 给执行者\n- x\n## 验收与保持\n- AC-1 a · 来源：D-1\n## 任务\n- [x] T-1 a\n  - 覆盖：AC-1\n- [ ] T-2 b\n  - 覆盖：AC-1\n"


class TestReqStatus(unittest.TestCase):
    def test_no_engineering_dir(self):
        code, out = run(Path(tempfile.mkdtemp()))
        self.assertEqual(code, 2)

    def test_progress_and_hint(self):
        root = make({"requirements/coupon/workspace/plan.md": PLAN,
                     "requirements/coupon/clarification/main.md": "x",
                     "requirements/coupon/reality.md": "- 基于：abc1234 · 2026-01-01\n"})
        code, out = run(root)
        self.assertEqual(code, 0, out)
        self.assertIn("任务 1/2", out)
        self.assertIn("「验收与保持」有", out)
        self.assertIn("基于 abc1234", out)
        self.assertIn("给执行者", out)
        self.assertIn("context.md：无", out)

    def test_block_review_routes_back(self):
        root = make({"requirements/coupon/workspace/plan.md": PLAN.replace("[ ] T-2", "[x] T-2"),
                     "requirements/coupon/reviews/20260101-abc1234.md": "# Verdict\n\nBLOCK\n"})
        plan = root / ".engineering/requirements/coupon/workspace/plan.md"
        old = time.time() - 100
        os.utime(plan, (old, old))
        code, out = run(root, "coupon")
        self.assertIn("BLOCK", out)
        self.assertIn("重新 test-readiness-review", out)

    def test_ready_review(self):
        root = make({"requirements/coupon/workspace/plan.md": PLAN.replace("[ ] T-2", "[x] T-2"),
                     "requirements/coupon/reviews/20260101-abc1234.md": "# Verdict\n\nREADY_FOR_TEST\n"})
        plan = root / ".engineering/requirements/coupon/workspace/plan.md"
        old = time.time() - 100
        os.utime(plan, (old, old))
        code, out = run(root, "coupon")
        self.assertIn("交给 QA", out)

    def test_unknown_slug(self):
        root = make({"requirements/coupon/workspace/plan.md": PLAN})
        code, out = run(root, "nope")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
