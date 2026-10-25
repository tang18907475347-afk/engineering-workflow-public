#!/usr/bin/env python3
"""结构回归：validator 不变量、生成副本与实际打包产物。

运行：python3 scripts/test_regressions.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REALITY = PLUGIN_ROOT / "skills" / "product-reality"
_SCRIPT = REALITY / "scripts" / "check_baseline.py"
_spec = importlib.util.spec_from_file_location("check_baseline", _SCRIPT)
cb = importlib.util.module_from_spec(spec=_spec)
_spec.loader.exec_module(cb)

ACTIVE_SKILLS = sorted([
    "ai-code-review",
    "bugfix",
    "implementation-strategy",
    "product-design",
    "product-engineering",
    "product-reality",
    "skill-architecture",
    "test-readiness-review",
    "work-retrospective",
])


def _run_checker(root: Path) -> tuple[int, str]:
    buf = io.StringIO()
    old = cb.sys.argv
    cb.sys.argv = ["check_baseline.py", str(root)]
    try:
        with contextlib.redirect_stdout(buf):
            code = cb.main()
    finally:
        cb.sys.argv = old
    return code, buf.getvalue()


def _valid() -> dict[str, str]:
    """一份完整、合法、status=COMPLETE 的 Current Reality fixture。"""
    return {
        "BASELINE_INDEX.md": """---
status: COMPLETE
---
# Baseline Index

## Baseline Scope
- Scope type: `module`
- Investigated: demo

## Subject Identity
| Subject | 系统 / 仓库 / 版本 | 角色 |
|---|---|---|
| `self` | demo@main | 被调查对象 |

## Subject Reality（derived profile）
| Capability / Area | declared | Implemented | Reachable | Executable | Experienced | Evidence refs | Confidence |
|---|---|---|---|---|---|---|---|
| 创建 | 是 | 是 | 是 | 是 | 是 | E-002 | 已确认 |

## Current Question
- Q-ID: Q-001
- Question: 创建流程如何
- Status: ANSWERED
- Evidence packet: packets/packet-1.md

## Next Work
1. 无
""",
        "product-model/INDEX.md": "# Product Model Index\n",
        "task-map/INDEX.md": """# Task Map

## L1 User Jobs
| J-ID | User Job | Trigger | Success | Core Object | Priority | Claim refs | Confidence |
|---|---|---|---|---|---|---|---|
| J-001 | 创建技能 | 点击新建 | 技能已创建 | Skill | P0 | C-001 | 已确认 |
""",
        "behavior/INDEX.md": "# Behavior Index\n",
        "evidence/INDEX.md": "# Evidence Index\n- packets/packet-1.md\n",
        "evidence/questions.md": """# Investigation Questions
| Q-ID | Question | Decision Impact | Required Evidence | Search Boundary | Status | Answer Claim refs | Open U-ID |
|---|---|---|---|---|---|---|---|
| Q-001 | 创建流程如何 | P0 | runtime | 单 Journey | ANSWERED | C-001 | - |
""",
        "evidence/claims.md": """# Claim Registry
| C-ID | Claim | Type | Reality facets | Evidence refs | Search Boundary / Boundary Status | Confidence | Replication Impact |
|---|---|---|---|---|---|---|---|
| C-001 | 创建流程端到端成立 | OBSERVED | implemented + experienced | E-001, E-002 | 单 Journey | 已确认 | - |
""",
        "evidence/unknowns.md": """# Unknown Registry
| U-ID | Unknown | Impact | Supporting Evidence | Contradicting Evidence | Required Authority | Status | Resolution C-ID |
|---|---|---|---|---|---|---|---|
""",
        "evidence/packets/packet-1.md": """# Evidence Packet — W-001

## Evidence
| E-ID | Subject | Channel | Reality | Kind | Locator | Observation | Boundary |
|---|---|---|---|---|---|---|---|
| E-001 | `self` | source | implemented |  | src/create.ts | 创建 handler 存在 | 单文件 |
| E-002 | `self` | runtime | experienced | interaction | modules/m1/verification/create.png | 点击后出现成功提示 | 单 Journey |
| E-003 | `self` | runtime | experienced | presentation | modules/m1/verification/home.png | 首屏为 composer | 单页 |
""",
        "coverage/INDEX.md": "# Coverage Index\n- journeys.md\n",
        "coverage/journeys.md": """# Coverage — Journeys

## Type Completeness
| Inventory Type | Item 数 | 若为 0：确实不存在 / 未找到 |
|---|---|---|
| Surface | 5 | - |
| Runtime Executor | 2 | - |
| Authoritative Docs | 3 | - |

## Journeys（广度）
| J-ID | Continuity Dimension | Status | B-ID / Claim refs |
|---|---|---|---|
| J-001 | 首次使用 | COVERED | C-001 |

## Journey 深度轴
| J-ID | interaction (`Kind: interaction`) | presentation (`Kind: presentation`) | experience observed (`Reality: experienced`) | Evidence refs |
|---|---|---|---|---|
| J-001 | PRESENT | PRESENT | PRESENT | E-002, E-003 |
""",
    }


def _write(files: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp(prefix="baseline-fixture-"))
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def _sub(files: dict[str, str], rel: str, old: str, new: str) -> dict[str, str]:
    out = dict(files)
    assert old in out[rel], f"fixture bug: {old!r} not in {rel}"
    out[rel] = out[rel].replace(old, new, 1)
    return out


class TestValidatorDeterminism(unittest.TestCase):
    def test_complete_non_ui_baseline_needs_no_experience_table(self):
        fixture = _valid()
        for path, content in fixture.items():
            fixture[path] = content.replace("创建技能", "生成日报").replace(
                "点击新建", "定时触发").replace("创建流程", "日报任务")
        fixture["evidence/packets/packet-1.md"] = (
            "# Evidence Packet\n"
            "| E-ID | Subject | Channel | Reality | Kind | Locator | Observation | Boundary |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| E-001 | self | source | implemented | | src/report.ts | 定时生成 | 日报任务 |\n"
            "| E-002 | self | test | executable | | tests/report.test.ts | 日报写入成功 | 测试环境 |\n")
        fixture["evidence/claims.md"] = fixture["evidence/claims.md"].replace(
            "implemented + experienced", "implemented + executable")
        fixture["BASELINE_INDEX.md"] = fixture["BASELINE_INDEX.md"].replace(
            "| 创建 | 是 | 是 | 是 | 是 | 是 |", "| 日报 | 是 | 是 | 是 | 是 | 不适用 |")
        fixture["coverage/journeys.md"] = (
            fixture["coverage/journeys.md"].split("## Journey 深度轴")[0]
            .replace("| Surface | 5 | - |", "| Surface | 0 | 确实不存在：非 UI 定时任务 |"))
        code, out = _run_checker(_write(fixture))
        self.assertEqual(code, 0, out)

    def test_present_depth_still_needs_evidence(self):
        fixture = _sub(_valid(), "coverage/journeys.md",
                       "| J-001 | PRESENT | PRESENT | PRESENT | E-002, E-003 |",
                       "| J-001 | PRESENT | PRESENT | PRESENT | - |")
        code, out = _run_checker(_write(fixture))
        self.assertEqual(code, 1, out)
        self.assertIn("PRESENT", out)

    def test_valid_baseline_passes(self):
        code, out = _run_checker(_write(_valid()))
        self.assertEqual(code, 0, f"合法 baseline 应 PASS，实际输出：\n{out}")

    def test_complete_without_evidence(self):
        f = _sub(_valid(), "evidence/packets/packet-1.md",
                 "| E-001 | `self` | source | implemented |  | src/create.ts | 创建 handler 存在 | 单文件 |\n"
                 "| E-002 | `self` | runtime | experienced | interaction | modules/m1/verification/create.png | 点击后出现成功提示 | 单 Journey |\n"
                 "| E-003 | `self` | runtime | experienced | presentation | modules/m1/verification/home.png | 首屏为 composer | 单页 |\n",
                 "")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("没有任何 canonical E-*", out)

    def test_coverage_present_dangling_evidence(self):
        f = _sub(_valid(), "coverage/journeys.md",
                 "| J-001 | PRESENT | PRESENT | PRESENT | E-002, E-003 |",
                 "| J-001 | PRESENT | PRESENT | PRESENT | E-999 |")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("悬空 Evidence 引用", out)

    def test_required_field_empty(self):
        f = _sub(_valid(), "evidence/packets/packet-1.md",
                 "| E-001 | `self` | source | implemented |  | src/create.ts | 创建 handler 存在 | 单文件 |",
                 "| E-001 | `self` | source | implemented |  |  | 创建 handler 存在 | 单文件 |")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("Locator 为空", out)

    def test_illegal_evidence_id_not_skipped(self):
        f = _sub(_valid(), "evidence/packets/packet-1.md",
                 "| E-002 | `self` | runtime | experienced |",
                 "| E-2x | `self` | runtime | experienced |")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("非法", out)

    def test_duplicate_evidence_id(self):
        f = _sub(_valid(), "evidence/packets/packet-1.md",
                 "| E-003 | `self` | runtime | experienced | presentation | modules/m1/verification/home.png | 首屏为 composer | 单页 |",
                 "| E-003 | `self` | runtime | experienced | presentation | modules/m1/verification/home.png | 首屏为 composer | 单页 |\n"
                 "| E-003 | `self` | source | implemented |  | src/x.ts | 重复定义 | 单文件 |")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("重复 Evidence ID", out)

    def test_packet_claim_copy_is_not_a_duplicate(self):
        """packets 中的历史 C-* 副本不算 canonical 定义；claims.md 才是 Claim Registry。"""
        f = _sub(_valid(), "evidence/packets/packet-1.md",
                 "## Evidence\n",
                 "## Historical Claim Copy\n"
                 "| C-ID | Claim | Type | Evidence refs |\n"
                 "|---|---|---|---|\n"
                 "| C-001 | 历史副本 | OBSERVED | E-001 |\n\n"
                 "## Evidence\n")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 0, f"packet 内历史 Claim 副本不得判重复，实际输出：\n{out}")

    def test_duplicate_claim_in_registry_still_fails(self):
        f = _sub(_valid(), "evidence/claims.md",
                 "| C-001 | 创建流程端到端成立 |",
                 "| C-001 | 创建流程端到端成立 |\n"
                 "| C-001 | 重复的 Claim 定义 |")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("重复 Claim ID", out)

    def test_depth_missing_blocks_complete(self):
        f = _sub(_valid(), "coverage/journeys.md",
                 "| J-001 | PRESENT | PRESENT | PRESENT | E-002, E-003 |",
                 "| J-001 | PRESENT | PRESENT | MISSING | E-002, E-003 |")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("不得 COMPLETE", out)

    def test_baseline_scope_and_single_replica_judgment(self):
        f = _sub(_valid(), "BASELINE_INDEX.md",
                 "## Baseline Scope\n- Scope type: `module`\n- Investigated: demo\n\n", "")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("Baseline Scope", out)

        f = _sub(_valid(), "BASELINE_INDEX.md", "## Next Work",
                 "## Replica-Ready Judgment\n- Replica-Ready: 是\n\n## Next Work")
        code, out = _run_checker(_write(f))
        self.assertEqual(code, 1)
        self.assertIn("must live in spec/INDEX.md", out)

    def test_spec_only_structural_anchors(self):
        spec = (
            "## Spec Target Scope\n- Target: x\n\n"
            "## Behavior Contracts\n| Inventory Item | B-ID |\n|---|---|\n\n"
            "## Replica-Ready Judgment\n- Replica-Ready: 否\n"
        )
        code, out = _run_checker(_write({"spec/INDEX.md": spec}))
        self.assertEqual(code, 0, out)

        code, out = _run_checker(_write({
            "spec/INDEX.md": spec.replace("## Behavior Contracts", "## Behaviors")}))
        self.assertEqual(code, 1)
        self.assertIn("Behavior Contracts", out)

        code, out = _run_checker(
            _write({"spec/a.md": spec, "spec/b.md": spec}))
        self.assertEqual(code, 1)
        self.assertIn("no INDEX.md", out)


class TestRuntimeResources(unittest.TestCase):
    def test_active_skill_set(self):
        got = sorted(p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir())
        self.assertEqual(got, ACTIVE_SKILLS)

    def test_shared_copies_match_generator(self):
        spec = importlib.util.spec_from_file_location(
            "sync_shared", PLUGIN_ROOT / "scripts" / "sync_shared_references.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for skill, names in mod.DEPENDENCIES.items():
            for name in names:
                source = (PLUGIN_ROOT / "shared" / name).read_text(encoding="utf-8")
                target = PLUGIN_ROOT / "skills" / skill / "references" / name
                self.assertEqual(target.read_text(encoding="utf-8"),
                                 mod.render(name, source), str(target))


class TestPluginPackaging(unittest.TestCase):
    def _build(self, target: str):
        spec = importlib.util.spec_from_file_location(
            "package_plugin", PLUGIN_ROOT / "scripts" / "package-plugin.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / f"{target}.zip"
            with contextlib.redirect_stdout(io.StringIO()):
                entries = mod.build_target(PLUGIN_ROOT, target, output)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
        return entries, names

    def test_qoder_package_contains_only_qoder_manifest(self):
        _entries, names = self._build("qoder")
        self.assertIn(".qoder-plugin/plugin.json", names)
        self.assertNotIn(".codex-plugin/plugin.json", names)
        self.assertIn("skills/product-engineering/SKILL.md", names)
        self.assertEqual(
            len([n for n in names if n.endswith("/SKILL.md")]), 9)

    def test_codex_package_contains_only_codex_manifest(self):
        _entries, names = self._build("codex")
        self.assertIn(".codex-plugin/plugin.json", names)
        self.assertNotIn(".qoder-plugin/plugin.json", names)
        self.assertIn(
            "skills/skill-architecture/references/format-compression.md",
            names)
        self.assertEqual(
            len([n for n in names if n.endswith("/SKILL.md")]), 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
