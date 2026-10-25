"""check_plan.py 的单元测试（unittest，不依赖外部服务）。

运行：python3 -m unittest discover -s skills/implementation-strategy/tests -v
"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_plan  # noqa: E402

GOOD = """# 计划

## 给执行者
- 按任务顺序推进

## 验收与保持
- AC-1 提交失败时保留输入 · 来源：D-2 · 验证：组件测试
- AC-2 两个字段都违规时都标红 · 来源：clarification/main.md#提交 · 验证：浏览器手测
- P-1 编辑时未修改字段不会被清空 · 来源：reality.md PC-1 · 验证：现有测试
- ~~AC-3 旧需求~~ 作废：产品取消

## 任务
### T-1 改接口层
覆盖：AC-1、P-1
### T-2 改界面
- 覆盖：AC-2
"""


def run(text: str, phase: str | None = None):
    d = Path(tempfile.mkdtemp())
    (d / "plan.md").write_text(text, encoding="utf-8")
    if phase:
        (d / "phase-01-ui.md").write_text(phase, encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check_plan.main(["check_plan.py", str(d)])
    return code, buf.getvalue()


class TestCheckPlan(unittest.TestCase):
    def test_good_plan_passes(self):
        code, out = run(GOOD)
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)

    def test_uncovered_ac_is_error(self):
        code, out = run(GOOD.replace("- 覆盖：AC-2", "- 覆盖：P-1"))
        self.assertEqual(code, 1, out)
        self.assertIn("AC-2 没有被任何任务覆盖", out)

    def test_struck_item_needs_no_coverage(self):
        code, out = run(GOOD)
        self.assertNotIn("AC-3", out)

    def test_missing_section_is_error_and_all_issues_reported(self):
        code, out = run("# 计划\n\n## 任务\n- [ ] T-1 做事\n")
        self.assertEqual(code, 1, out)
        self.assertIn("缺少「验收与保持」", out)
        self.assertIn("缺少「给执行者」", out)
        self.assertIn("T-1 没有关联任何 AC / P", out)

    def test_unknown_reference_and_duplicate(self):
        text = GOOD.replace("覆盖：AC-1、P-1", "覆盖：AC-1、P-1、AC-9") + "- AC-1 重复\n"
        text = text.replace("## 任务", "- AC-1 重复 · 来源：x\n\n## 任务", 1)
        code, out = run(text)
        self.assertEqual(code, 1, out)
        self.assertIn("引用了不存在的 AC-9", out)
        self.assertIn("AC-1 重复定义", out)

    def test_tasks_in_phase_file_count(self):
        plan = GOOD.split("## 任务")[0]
        phase = "# Phase 1\n- [ ] T-1 a\n  - 覆盖：AC-1、P-1\n- [x] T-2 b\n  - 覆盖：AC-2\n"
        code, out = run(plan, phase)
        self.assertEqual(code, 0, out)

    def test_source_and_locator_warnings(self):
        text = GOOD.replace(" · 来源：D-2", "").replace("来源：reality.md PC-1", "来源：口头")
        code, out = run(text)
        self.assertEqual(code, 0, out)
        self.assertIn("AC-1 没有写来源", out)
        self.assertIn("P-1 既没引用", out)

    def test_missing_plan_is_usage_error(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = check_plan.main(["check_plan.py", "/nonexistent/workspace"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
