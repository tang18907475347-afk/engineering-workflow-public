#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ai-code-review 脚本的本地单元测试（不访问网络 / 平台）。

运行：
  python3 -m unittest discover -s skills/ai-code-review/tests -v
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import review  # noqa: E402
import review_artifact  # noqa: E402
import review_contract  # noqa: E402
import review_html  # noqa: E402


def raw_comment(**overrides):
    base = {
        "id": 101,
        "note": "![缺陷 · 中](https://img.shields.io/badge/x)\n\n`foo` 可能为空。",
        "path": "src/a.ts",
        "line": 12,
        "lineRange": {"fromLine": 10, "toLine": 12},
        "context": "oldsha newsha",
        "outdated": False,
        "closed": 0,
        "adopted": 1,
        "parentNoteId": None,
        "aiComment": True,
        "coAuthor": {"username": "codereview-copilot"},
        "createdAt": 1700000000000,
        "updatedAt": 1700000000000,
        "notesCodeDiffContext": "@@ -1 +1 @@",
    }
    base.update(overrides)
    return base


def ns(**overrides):
    defaults = dict(
        repo="foo/bar", mr=1, worktree=tempfile.mkdtemp(prefix="ai-review-wt-"),
        id=101, action="reject", reason_code=None, reason=None,
        confirm=False, include_handled=False, json=False, state="pending",
        severity=None, path=None, ids=None, limit=None, note=None,
        note_file=None, out=None, artifact=None, envelope=None,
        patch=None, allow_incomplete=False, dry_run=False,
        include_closed=False, force=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class FakeRunner:
    def __init__(self, comments):
        self.comments = comments
        self.calls = []

    def __call__(self, tool, payload, **kwargs):
        self.calls.append((tool, payload, kwargs))
        if tool == "list_merge_request_ai_comments":
            return self.comments
        if tool == "get_merge_request_detail":
            return {
                "id": 42188, "iid": 711, "state": "opened",
                "title": "test MR", "sourceBranch": "feat/x",
                "targetBranch": "master", "mergeStatus": "can_be_merged",
                "webUrl": "https://gitlab.example.com/foo/bar",
            }
        if tool == "list_merge_request_changed_files":
            return {"count": 3, "totalAddLines": 10, "totalDelLines": 2}
        return {"ok": True}


def make_analysis(**overrides):
    base = {
        "issueRisk": "medium",
        "assessment": "CONFIRMED",
        "recommendation": "FIX",
        "trigger": "输入框失焦时值为空",
        "impact": "提交空值或触发异常",
        "rootCause": "回退逻辑覆盖了空值",
        "evidence": [
            {"kind": "OBSERVED", "ref": "src/a.ts:12", "summary": "回退逻辑"},
        ],
        "openQuestions": [],
        "proposal": {
            "summary": "修正空值回退",
            "approach": "在 owner 中保留空值判断，不覆盖调用方输入",
            "files": ["src/a.ts"],
            "owner": "CourseForm",
            "changes": ["调整回退条件", "补一个回归测试"],
            "verification": ["npm test -- course-form"],
            "scope": "local",
            "fixRisk": "medium",
            "alternatives": [],
        },
    }
    base.update(overrides)
    return base


def make_finding(finding_id=101, **analysis_overrides):
    source = {
        "note": "![缺陷 · 中](x)\n\n`foo` 可能为空。",
        "path": "src/a.ts",
        "line": 12,
        "lineRange": {"fromLine": 12, "toLine": 12},
        "context": "old new",
        "outdated": False,
        "platformState": "pending",
        "platform": {"adopted": 1, "closed": 0},
        "platformInterpretation": "PENDING",
        "diffContext": "@@ -1 +1 @@",
        "suggestion": None,
        "author": "copilot",
        "updatedAt": "2026-10-21T10:00:00",
    }
    finding = {
        "id": finding_id,
        "proposalFingerprint": None,
        "source": source,
        "analysis": make_analysis(**analysis_overrides),
    }
    finding["proposalFingerprint"] = review_contract.compute_proposal_fingerprint(
        finding)
    return finding


def make_closed_finding(finding_id=201):
    finding = make_finding(finding_id)
    source = dict(finding["source"])
    source["platform"] = {"adopted": 0, "closed": 1}
    source["platformState"] = "handled"
    source["platformInterpretation"] = "CLOSED_NOT_ADOPTED"
    return {"id": finding_id, "source": source}


def make_artifact(findings=None, head_matches=True):
    if findings is None:
        findings = [make_finding()]
    return {
        "schemaVersion": 1,
        "reviewKey": "foo/bar#1",
        "artifactPath": ".engineering/work/ai-review/foo__bar__1__abc/review.json",
        "generatedAt": "2026-10-21T10:00:00+08:00",
        "repo": "foo/bar",
        "mergeRequestId": 1,
        "iid": 711,
        "mrUrl": "https://gitlab.example.com/foo/bar/-/merge_requests/711",
        "sourceBranch": "feat/x",
        "targetBranch": "master",
        "reviewHead": "abc",
        "worktreeHead": "abc",
        "headMatches": head_matches,
        "selection": {"mode": "all", "requestedIds": []},
        "preflight": {},
        "summary": {"total": len(findings)},
        "findings": findings,
        "closedFindings": [],
    }


class TestParsing(unittest.TestCase):
    def test_parse_chinese_badge(self):
        category, severity, title = review.parse_badge(
            "![缺陷 · 中](https://img.shields.io/badge/x)\n\n`foo` 可能为空。")
        self.assertEqual(category, "缺陷")
        self.assertEqual(severity, "medium")
        self.assertTrue(title.startswith("`foo`"))

    def test_parse_badge_without_badge(self):
        category, severity, title = review.parse_badge("普通评论\n第二行")
        self.assertEqual((category, severity), ("unknown", "unknown"))
        self.assertEqual(title, "普通评论")

    def test_platform_state(self):
        self.assertEqual(review.platform_state(1, 0), "pending")
        self.assertEqual(review.platform_state(3, 1), "handled")
        self.assertEqual(review.platform_state(1, 1), "handled")
        self.assertEqual(review.platform_state(None, 0), "unknown")

    def test_normalize_supports_comments_shape(self):
        raw = {
            "id": 7, "body": "![安全 · 高](x)\n\n风险", "filePath": "b.ts",
            "lineNumber": 3, "isAiComment": True, "closed": 0, "adopted": 1,
            "parentNoteId": None,
        }
        comment = review.normalize_comment(raw, head_sha=None)
        self.assertEqual(comment["category"], "安全")
        self.assertEqual(comment["severity"], "high")
        self.assertEqual(comment["path"], "b.ts")
        self.assertEqual(comment["line"], 3)
        self.assertTrue(comment["ai_comment"])
        self.assertEqual(comment["state"], "pending")

    def test_outdated_is_not_handled(self):
        comment = review.normalize_comment(raw_comment(outdated=True))
        self.assertTrue(comment["outdated"])
        self.assertEqual(comment["state"], "pending")

    def test_head_match(self):
        comment = review.normalize_comment(
            raw_comment(context="old abcdef123456"), head_sha="abcdef1234567890")
        self.assertTrue(comment["head_matches"])

    def test_normalize_repo(self):
        self.assertEqual(review.normalize_repo(
            "git@gitlab.example.com:acme/webapp.git"),
            "acme/webapp")
        self.assertEqual(review.normalize_repo(
            "https://gitlab.example.com/acme/webapp"),
            "acme/webapp")
        self.assertEqual(review._remote_host(
            "git@gitlab.example.com:acme/webapp.git"),
            "gitlab.example.com")
        self.assertEqual(review._remote_host(
            "ssh://git@gitlab.example.com/acme/webapp.git"),
            "gitlab.example.com")

    def test_mr_web_url_uses_repo_and_iid(self):
        with unittest.mock.patch.dict(os.environ, {"GITLAB_HOST": "gitlab.example.com"}):
            self.assertEqual(
                review.mr_web_url("foo/bar", 711),
                "https://gitlab.example.com/foo/bar/-/merge_requests/711")
            self.assertEqual(
                review.mr_web_url("foo/bar", 711, worktree=None),
                "https://gitlab.example.com/foo/bar/-/merge_requests/711")
        self.assertEqual(
            review.mr_web_url(
                "foo/bar", 711,
                base_url="https://gitlab.example.com/foo/bar"),
            "https://gitlab.example.com/foo/bar/-/merge_requests/711")
        self.assertIsNone(review.mr_web_url("foo/bar", None))


class TestFiltering(unittest.TestCase):
    def test_filter_by_severity_and_path(self):
        comments = [
            review.normalize_comment(raw_comment(id=1, path="src/a.ts")),
            review.normalize_comment(raw_comment(
                id=2, path="src/b.ts", note="![缺陷 · 高](x)\n\nB")),
            review.normalize_comment(raw_comment(
                id=3, path="src/a.ts", note="![风格 · 低](x)\n\nC", adopted=3, closed=1)),
        ]
        matched = review.filter_comments(
            comments, state="pending", severities={"high"}, path="b")
        self.assertEqual([item["id"] for item in matched], [2])

    def test_filter_by_kind_ignored(self):
        comments = [
            review.normalize_comment(raw_comment(id=1, adopted=3, closed=1)),
            review.normalize_comment(raw_comment(id=2, adopted=1, closed=0)),
        ]
        self.assertEqual(
            [c["id"]
                for c in review.filter_comments(comments, state="ignored")],
            [1])
        # handled 仍包含 ignored（closed=1），与原有粗粒度语义一致。
        self.assertEqual(
            [c["id"]
                for c in review.filter_comments(comments, state="handled")],
            [1])

    def test_find_missing_raises(self):
        with self.assertRaises(review.ReviewError):
            review.find_comment([], 999)


class TestFeedbackValidation(unittest.TestCase):
    def test_reject_requires_reason(self):
        with self.assertRaises(review.ReviewError):
            review.validate_feedback("reject", None, None)

    def test_reject_rejects_unknown_code(self):
        with self.assertRaises(review.ReviewError):
            review.validate_feedback("reject", "LOW_PRIORITY", None)

    def test_ignore_rejects_unknown_code(self):
        with self.assertRaises(review.ReviewError):
            review.validate_feedback("ignore", "AI_MISJUDGED", None)

    def test_reject_accepts_valid_code(self):
        review.validate_feedback("reject", "AI_MISJUDGED", None)

    def test_adopt_rejects_reason_code(self):
        with self.assertRaises(review.ReviewError):
            review.validate_feedback("adopt", "AI_MISJUDGED", None)

    def test_adopt_accepts_free_text(self):
        review.validate_feedback("adopt", None, "已修复并验证")


class TestCommands(unittest.TestCase):
    def test_feedback_refuses_handled_without_include_handled(self):
        runner = FakeRunner([raw_comment(adopted=3, closed=1)])
        args = ns(action="reject", reason_code="AI_MISJUDGED")
        with self.assertRaises(review.ReviewError) as ctx:
            review.cmd_feedback(args, runner=runner)
        self.assertIn("--include-handled", str(ctx.exception))

    def test_feedback_include_handled_allows_override(self):
        runner = FakeRunner([raw_comment(adopted=3, closed=1)])
        args = ns(action="reject", reason_code="AI_MISJUDGED",
                  include_handled=True, confirm=True)
        with contextlib.redirect_stdout(io.StringIO()):
            code = review.cmd_feedback(args, runner=runner)
        self.assertEqual(code, 0)
        self.assertEqual(runner.calls[-1][0], "operate_ai_comment")

    def test_feedback_confirm_payload(self):
        runner = FakeRunner([raw_comment()])
        args = ns(action="ignore", reason_code="KNOWN_ISSUE", confirm=True)
        with contextlib.redirect_stdout(io.StringIO()):
            review.cmd_feedback(args, runner=runner)
        tool, payload, kwargs = runner.calls[-1]
        self.assertEqual(tool, "operate_ai_comment")
        self.assertEqual(payload["noteId"], 101)
        self.assertEqual(payload["action"], "ignore")
        self.assertEqual(payload["reason"], "KNOWN_ISSUE")
        self.assertFalse(kwargs.get("retry", True))

    def test_reply_rejects_non_top_level(self):
        runner = FakeRunner([raw_comment(parentNoteId=99)])
        args = ns(note="evidence")
        with self.assertRaises(review.ReviewError):
            review.cmd_reply(args, runner=runner)

    def test_reply_dry_run_payload(self):
        runner = FakeRunner([raw_comment()])
        args = ns(note="Local assessment: DISMISSED\n证据：...")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = review.cmd_reply(args, runner=runner)
        self.assertEqual(code, 0)
        self.assertIn("comment_merge_request", buf.getvalue())
        self.assertNotIn("comment_merge_request", [
                         call[0] for call in runner.calls])

    def test_list_json_is_pure_json(self):
        runner = FakeRunner([
            raw_comment(id=1),
            raw_comment(id=2, note="![缺陷 · 高](x)\n\nB"),
            raw_comment(id=3, adopted=3, closed=1),
        ])
        args = ns(state="pending", severity="high", json=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = review.cmd_list(args, runner=runner)
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["matched"], 1)
        self.assertEqual(payload["comments"][0]["id"], 2)

    def test_list_warns_head_mismatch(self):
        comments = [review.normalize_comment(
            raw_comment(context="old deadbeef"), "cafebabe")]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            review._print_list(
                "foo/bar", 1, comments, comments,
                {"head": "cafebabe", "branch": "feat/x", "matches": True},
                "feat/x")
        output = buf.getvalue()
        self.assertIn("WARN:", output)
        self.assertIn("deadbeef", output)
        self.assertIn("feat/x", output)

    def test_mr_summary_has_separate_id_iid_and_mr_url(self):
        runner = FakeRunner([])
        args = ns(json=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = review.cmd_mr(args, runner=runner)
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["id"], 42188)
        self.assertEqual(payload["iid"], 711)
        self.assertTrue(payload["webUrl"].endswith("/-/merge_requests/711"))
        self.assertEqual(payload["projectUrl"],
                         "https://gitlab.example.com/foo/bar")
        self.assertEqual(payload["changedFiles"], 3)


class TestReviewContract(unittest.TestCase):
    def test_acceptance_is_boolean_and_fingerprinted(self):
        finding = make_finding()
        original = finding["proposalFingerprint"]
        finding["analysis"]["proposal"]["requiresHumanAcceptance"] = False
        updated = review_contract.compute_proposal_fingerprint(finding)
        self.assertNotEqual(updated, original)
        finding["proposalFingerprint"] = updated
        self.assertEqual(review_contract.validate_finding_analysis(finding), [])
        for value in ("false", 0, None):
            with self.subTest(value=value):
                finding["analysis"]["proposal"]["requiresHumanAcceptance"] = value
                finding["proposalFingerprint"] = review_contract.compute_proposal_fingerprint(finding)
                self.assertTrue(review_contract.validate_finding_analysis(finding))

    def test_acceptance_cannot_be_overridden_or_omitted_in_new_envelope(self):
        for expected in (True, False):
            finding = make_finding()
            finding["analysis"]["proposal"]["requiresHumanAcceptance"] = expected
            finding["proposalFingerprint"] = review_contract.compute_proposal_fingerprint(finding)
            artifact = make_artifact([finding])
            for supplied in (True, False, None, "false"):
                with self.subTest(expected=expected, supplied=supplied):
                    decision = {"findingId": 101, "status": "APPROVE",
                                "proposalFingerprint": finding["proposalFingerprint"]}
                    if supplied is not None:
                        decision["requiresHumanAcceptance"] = supplied
                    envelope = {"schemaVersion": 1, "reviewKey": artifact["reviewKey"],
                                "decisions": [decision]}
                    errors, authorized, stale, invalid = review_contract.validate_decision_envelope(envelope, artifact)
                    self.assertEqual(errors, [])
                    self.assertEqual(stale, [])
                    self.assertEqual(authorized, [101] if supplied is expected else [])
                    self.assertEqual(len(invalid), 0 if supplied is expected else 1)

    def test_review_key_is_stable(self):
        self.assertEqual(
            review_contract.compute_review_key("foo/bar", 42187),
            "foo/bar#42187")

    def test_fingerprint_ignores_source_changes_but_tracks_analysis(self):
        finding = make_finding()
        first = review_contract.compute_proposal_fingerprint(finding)
        finding["source"]["note"] = "changed comment"
        finding["source"]["line"] = 99
        self.assertEqual(
            review_contract.compute_proposal_fingerprint(finding), first)
        finding["analysis"]["proposal"]["summary"] = "new approach"
        self.assertNotEqual(
            review_contract.compute_proposal_fingerprint(finding), first)

    def test_fingerprint_covers_validity_evidence_and_both_risks(self):
        base = review_contract.compute_proposal_fingerprint(make_finding())
        self.assertNotEqual(
            review_contract.compute_proposal_fingerprint(
                make_finding(rootCause="new root cause")), base)
        self.assertNotEqual(
            review_contract.compute_proposal_fingerprint(
                make_finding(issueRisk="high")), base)
        self.assertNotEqual(
            review_contract.compute_proposal_fingerprint(
                make_finding(evidence=[
                    {"kind": "OBSERVED", "ref": "src/a.ts:13",
                     "summary": "new evidence"}])), base)
        self.assertNotEqual(
            review_contract.compute_proposal_fingerprint(
                make_finding(proposal={
                    "summary": "x", "approach": "y", "files": ["src/a.ts"],
                    "owner": "CourseForm", "changes": [],
                    "verification": ["npm test"], "scope": "local",
                    "fixRisk": "high", "alternatives": []})), base)

    def test_validate_artifact_accepts_complete(self):
        artifact = make_artifact()
        self.assertEqual(
            review_contract.validate_review_artifact(artifact), [])

    def test_validate_artifact_accepts_closed_only(self):
        artifact = make_artifact([])
        artifact["closedFindings"] = [make_closed_finding()]
        self.assertEqual(
            review_contract.validate_review_artifact(artifact), [])

    def test_validate_artifact_rejects_analysis_on_closed(self):
        closed = make_closed_finding()
        closed["analysis"] = make_analysis()
        artifact = make_artifact([])
        artifact["closedFindings"] = [closed]
        errors = review_contract.validate_review_artifact(artifact)
        self.assertTrue(any("只汇报" in error for error in errors))

    def test_validate_artifact_rejects_duplicate_closed_id(self):
        artifact = make_artifact([make_finding(101)])
        artifact["closedFindings"] = [make_closed_finding(101)]
        errors = review_contract.validate_review_artifact(artifact)
        self.assertTrue(any("重复" in error for error in errors))

    def test_validate_artifact_rejects_empty_active_and_closed(self):
        artifact = make_artifact([])
        errors = review_contract.validate_review_artifact(artifact)
        self.assertTrue(any("至少有一个非空" in error for error in errors))

    def test_validate_artifact_rejects_missing_analysis(self):
        finding = make_finding()
        finding["analysis"] = None
        finding["proposalFingerprint"] = None
        errors = review_contract.validate_review_artifact(
            make_artifact([finding]))
        self.assertTrue(any("analysis" in error for error in errors))

    def test_validate_artifact_rejects_fingerprint_mismatch(self):
        artifact = make_artifact()
        artifact["findings"][0]["proposalFingerprint"] = "deadbeef"
        errors = review_contract.validate_review_artifact(artifact)
        self.assertTrue(
            any("proposalFingerprint" in error for error in errors))

    def test_validate_artifact_rejects_platform_mismatch(self):
        artifact = make_artifact()
        artifact["findings"][0]["source"]["platformInterpretation"] = (
            "CLOSED_NOT_ADOPTED")
        errors = review_contract.validate_review_artifact(artifact)
        self.assertTrue(any("平台字段不一致" in error for error in errors))

    def test_validate_artifact_rejects_inconsistent_assessment(self):
        finding = make_finding(
            assessment="DISMISSED", recommendation="FIX")
        errors = review_contract.validate_review_artifact(
            make_artifact([finding]))
        self.assertTrue(any("不一致" in error for error in errors))

    def test_dismissed_can_have_no_root_cause(self):
        finding = make_finding(
            assessment="DISMISSED", recommendation="DISMISS",
            proposal=None, rootCause="")
        artifact = make_artifact([finding])
        self.assertEqual(
            review_contract.validate_review_artifact(artifact), [])

    def test_validate_envelope_authorizes_approve_and_close(self):
        artifact = make_artifact([
            make_finding(101),
            make_finding(102),
            make_finding(103),
        ])
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [
                {"findingId": 101,
                 "proposalFingerprint": artifact["findings"][0]["proposalFingerprint"],
                 "status": "APPROVE"},
                {"findingId": 102,
                 "proposalFingerprint": artifact["findings"][1]["proposalFingerprint"],
                 "status": "CLOSE", "note": "本 MR 不处理，另单跟踪"},
                {"findingId": 103,
                 "proposalFingerprint": artifact["findings"][2]["proposalFingerprint"],
                 "status": "UNDECIDED"},
            ],
        }
        errors, authorized, stale, invalid = (
            review_contract.validate_decision_envelope(envelope, artifact))
        self.assertEqual(errors, [])
        # UNDECIDED 不授权也不报错，所以 authorized 只有 101 / 102。
        self.assertEqual(authorized, [101, 102])
        self.assertEqual(stale, [])
        self.assertEqual(invalid, [])

    def test_validate_envelope_stale_is_per_finding(self):
        artifact = make_artifact()
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [{
                "findingId": 101,
                "proposalFingerprint": "deadbeef",
                "status": "APPROVE",
            }],
        }
        errors, authorized, stale, invalid = (
            review_contract.validate_decision_envelope(envelope, artifact))
        self.assertEqual(errors, [])
        self.assertEqual(authorized, [])
        self.assertEqual([item["findingId"] for item in stale], [101])
        self.assertEqual(invalid, [])

    def test_validate_envelope_missing_fingerprint_is_stale(self):
        artifact = make_artifact()
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [{
                "findingId": 101,
                "status": "APPROVE",
            }],
        }
        errors, authorized, stale, invalid = (
            review_contract.validate_decision_envelope(envelope, artifact))
        self.assertEqual(errors, [])
        self.assertEqual(authorized, [])
        self.assertEqual([item["findingId"] for item in stale], [101])
        self.assertEqual(invalid, [])

    def test_validate_envelope_close_requires_note(self):
        artifact = make_artifact()
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [{
                "findingId": 101,
                "proposalFingerprint": artifact["findings"][0]["proposalFingerprint"],
                "status": "CLOSE",
            }],
        }
        errors, authorized, stale, invalid = (
            review_contract.validate_decision_envelope(envelope, artifact))
        self.assertEqual(errors, [])
        self.assertEqual(authorized, [])
        self.assertEqual(stale, [])
        self.assertEqual([item["findingId"] for item in invalid], [101])
        self.assertIn("理由", invalid[0]["reason"])

    def test_validate_envelope_approve_requires_fix_proposal(self):
        artifact = make_artifact([
            make_finding(101, recommendation="DISMISS", proposal=None),
        ])
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [{
                "findingId": 101,
                "proposalFingerprint": artifact["findings"][0]["proposalFingerprint"],
                "status": "APPROVE",
            }],
        }
        errors, authorized, stale, invalid = (
            review_contract.validate_decision_envelope(envelope, artifact))
        self.assertEqual(errors, [])
        self.assertEqual(authorized, [])
        self.assertEqual(stale, [])
        self.assertEqual([item["findingId"] for item in invalid], [101])

    def test_validate_envelope_proposal_change_invalidates_authorization(self):
        # proposal 属 fingerprint 覆盖范围：方案语义变化 -> 旧授权 stale。
        finding = make_finding(101)
        artifact = make_artifact([finding])
        old_fp = finding["proposalFingerprint"]
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [{
                "findingId": 101,
                "proposalFingerprint": old_fp,
                "status": "APPROVE",
            }],
        }
        _, authorized, _, _ = review_contract.validate_decision_envelope(
            envelope, artifact)
        self.assertEqual(authorized, [101])
        # 方案 approach 变化（人审批的是方案语义，不是补丁）。
        finding["analysis"]["proposal"]["approach"] = "改为在共享状态所有者处统一约束取消后的结果提交"
        finding["proposalFingerprint"] = (
            review_contract.compute_proposal_fingerprint(finding))
        self.assertNotEqual(finding["proposalFingerprint"], old_fp)
        _, authorized, stale, _ = review_contract.validate_decision_envelope(
            envelope, artifact)
        self.assertEqual(authorized, [])
        self.assertEqual([item["findingId"] for item in stale], [101])

    def test_platform_interpretation_closed_not_adopted(self):
        self.assertEqual(
            review_contract.platform_interpretation(0, 1),
            "CLOSED_NOT_ADOPTED")
        self.assertEqual(
            review_contract.platform_interpretation(1, 0), "PENDING")

    def test_platform_interpretation_ignored_only_for_observed(self):
        # 3/1 是已观测的“已忽略”组合；2/4 缺样本不猜，落 CLOSED_WITH_ACTION。
        self.assertEqual(
            review_contract.platform_interpretation(3, 1), "IGNORED")
        self.assertEqual(
            review_contract.platform_interpretation(2, 1), "CLOSED_WITH_ACTION")
        self.assertEqual(
            review_contract.platform_interpretation(4, 1), "CLOSED_WITH_ACTION")
        self.assertIn("IGNORED", review_contract.PLATFORM_INTERPRETATIONS)

    def test_platform_kind_derives_from_interpretation(self):
        self.assertEqual(review.platform_kind(1, 0), "pending")
        self.assertEqual(review.platform_kind(3, 1), "ignored")
        self.assertEqual(review.platform_kind(0, 1), "closed")
        self.assertEqual(review.platform_kind(2, 1), "closed")
        self.assertEqual(review.platform_kind(None, None), "unknown")

    def test_normalize_carries_interpretation_and_kind(self):
        comment = review.normalize_comment(raw_comment(adopted=3, closed=1))
        self.assertEqual(comment["interpretation"], "IGNORED")
        self.assertEqual(comment["kind"], "ignored")
        self.assertEqual(comment["state"], "handled")


class TestArtifact(unittest.TestCase):
    def test_build_artifact_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = review_artifact.build_artifact(
                "foo/bar", 1,
                {"id": 1, "iid": 711, "sourceBranch": "feat/x",
                 "targetBranch": "master",
                 "webUrl": "https://gitlab.example.com/foo/bar"},
                [
                    raw_comment(id=101),
                    raw_comment(id=102, adopted=0, closed=1,
                                note="![缺陷 · 高](x)\n\nB"),
                ],
                directory,
            )
        self.assertEqual(artifact["reviewKey"], "foo/bar#1")
        self.assertEqual(artifact["iid"], 711)
        self.assertEqual(
            artifact["mrUrl"],
            "https://gitlab.example.com/foo/bar/-/merge_requests/711")
        self.assertEqual(len(artifact["findings"]), 1)
        self.assertEqual(len(artifact["closedFindings"]), 1)
        self.assertIsNone(artifact["findings"][0]["analysis"])
        source = artifact["findings"][0]["source"]
        self.assertEqual(source["category"], "缺陷")
        self.assertEqual(source["severity"], "medium")
        self.assertEqual(source["severityLabel"], "中")
        self.assertTrue(source["title"])
        self.assertEqual(
            artifact["closedFindings"][0]["source"]["platformInterpretation"],
            "CLOSED_NOT_ADOPTED")
        self.assertEqual(artifact["summary"]["total"], 2)
        self.assertEqual(artifact["summary"]["active"], 1)
        self.assertEqual(artifact["summary"]["closed"], 1)
        self.assertEqual(artifact["summary"]
                         ["platform"]["states"]["handled"], 1)
        self.assertEqual(artifact["summary"]
                         ["platform"]["states"]["pending"], 1)
        self.assertIsNone(artifact["preflight"]["dirty"])
        self.assertEqual(artifact["preflight"]["dirtyFiles"], [])
        self.assertIsNone(artifact["preflight"]["branchMatchesSource"])
        self.assertEqual(artifact["selection"],
                         {"mode": "all", "requestedIds": []})

    def test_build_artifact_can_include_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = review_artifact.build_artifact(
                "foo/bar", 1,
                {"id": 1, "iid": 711, "sourceBranch": "feat/x",
                 "targetBranch": "master",
                 "webUrl": "https://gitlab.example.com/foo/bar"},
                [raw_comment(id=101, adopted=0, closed=1)],
                directory, include_closed=True,
            )
        self.assertEqual(len(artifact["findings"]), 1)
        self.assertEqual(artifact["closedFindings"], [])
        self.assertEqual(artifact["summary"]["active"], 1)
        self.assertEqual(artifact["summary"]["closed"], 0)

    def test_build_artifact_propagates_ignored(self):
        # 端到端不变量：adopted=3/closed=1 在 Artifact 里也落 IGNORED，
        # 与 CLI normalize / HTML 消费同一个 platform_interpretation。
        with tempfile.TemporaryDirectory() as directory:
            artifact = review_artifact.build_artifact(
                "foo/bar", 1,
                {"id": 1, "iid": 711, "sourceBranch": "feat/x",
                 "targetBranch": "master",
                 "webUrl": "https://gitlab.example.com/foo/bar"},
                [raw_comment(id=101, adopted=3, closed=1)],
                directory, include_closed=True,
            )
        self.assertEqual(
            artifact["findings"][0]["source"]["platformInterpretation"],
            "IGNORED")

    def test_build_artifact_state_selection(self):
        # 能力不因平台状态被门控：默认只分析 pending，--state all/ignored 可重分析任意状态。
        detail = {"id": 1, "iid": 711, "sourceBranch": "feat/x",
                  "targetBranch": "master",
                  "webUrl": "https://gitlab.example.com/foo/bar"}
        comments = [raw_comment(id=101, adopted=1, closed=0),
                    raw_comment(id=102, adopted=3, closed=1)]
        with tempfile.TemporaryDirectory() as d:
            default = review_artifact.build_artifact(
                "foo/bar", 1, detail, comments, d,
                artifact_path=f"{d}/default.json")
            self.assertEqual([f["id"] for f in default["findings"]], [101])
            self.assertEqual([f["id"] for f in default["closedFindings"]], [102])
            everything = review_artifact.build_artifact(
                "foo/bar", 1, detail, comments, d,
                artifact_path=f"{d}/all.json", state="all")
            self.assertEqual(len(everything["findings"]), 2)
            self.assertEqual(everything["closedFindings"], [])
            ignored = review_artifact.build_artifact(
                "foo/bar", 1, detail, comments, d,
                artifact_path=f"{d}/ig.json", state="ignored")
            self.assertEqual([f["id"] for f in ignored["findings"]], [102])

    def test_cmd_artifact_writes_file(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            runner = FakeRunner([raw_comment()])
            args = ns(out=str(out))
            with contextlib.redirect_stdout(io.StringIO()):
                code = review_artifact.cmd_artifact(args, runner=runner)
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["reviewKey"], "foo/bar#1")
            self.assertEqual(data["findings"][0]["id"], 101)

    def test_cmd_artifact_can_limit_to_pilot_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            runner = FakeRunner([
                raw_comment(id=101),
                raw_comment(id=102),
            ])
            args = ns(out=str(out), ids="101")
            with contextlib.redirect_stdout(io.StringIO()):
                code = review_artifact.cmd_artifact(args, runner=runner)
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual([finding["id"]
                             for finding in data["findings"]], [101])
            self.assertEqual(data["selection"],
                             {"mode": "ids", "requestedIds": [101]})

    def test_cmd_artifact_refuses_overwrite_existing_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            original = make_artifact([make_finding(101)])
            out.write_text(json.dumps(original), encoding="utf-8")
            runner = FakeRunner([raw_comment()])
            with self.assertRaises(review.ReviewError) as ctx:
                review_artifact.cmd_artifact(ns(out=str(out)), runner=runner)
            self.assertIn("拒绝覆盖", str(ctx.exception))
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")),
                             original)

    def test_cmd_artifact_force_can_replace_existing_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            out.write_text(json.dumps(make_artifact([make_finding(101)])),
                           encoding="utf-8")
            runner = FakeRunner([raw_comment()])
            with contextlib.redirect_stdout(io.StringIO()):
                code = review_artifact.cmd_artifact(
                    ns(out=str(out), force=True), runner=runner)
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIsNone(data["findings"][0]["analysis"])

    def test_cmd_artifact_can_include_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            runner = FakeRunner([raw_comment(adopted=0, closed=1)])
            args = ns(out=str(out), include_closed=True)
            with contextlib.redirect_stdout(io.StringIO()):
                code = review_artifact.cmd_artifact(args, runner=runner)
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["closedFindings"], [])

    def test_cmd_artifact_without_comments_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            runner = FakeRunner([])
            args = ns(out=str(out))
            with self.assertRaises(review.ReviewError):
                review_artifact.cmd_artifact(args, runner=runner)
            self.assertFalse(out.exists())

    def test_cmd_artifact_notes_all_handled(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "review.json"
            runner = FakeRunner([raw_comment(adopted=0, closed=1)])
            args = ns(out=str(out))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = review_artifact.cmd_artifact(args, runner=runner)
            self.assertEqual(code, 0)
            self.assertIn("全部评论已是 handled", buf.getvalue())
            self.assertIn("不要把 closed 当成已修复", buf.getvalue())
            self.assertIn("CLOSED_NOT_ADOPTED", buf.getvalue())


class TestPatch(unittest.TestCase):
    def test_patch_acceptance_updates_authorization_fingerprint(self):
        artifact = make_artifact()
        old_fp = artifact["findings"][0]["proposalFingerprint"]
        patch = {"schemaVersion": 1, "reviewKey": artifact["reviewKey"],
                 "findings": [{"id": 101, "set": {
                     "proposal.requiresHumanAcceptance": False}}]}
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            with contextlib.redirect_stdout(io.StringIO()):
                code = review.cmd_patch(ns(artifact=str(artifact_path), patch=str(patch_path)))
            self.assertEqual(code, 0)
            updated = json.loads(artifact_path.read_text(encoding="utf-8"))
        finding = updated["findings"][0]
        self.assertIs(finding["analysis"]["proposal"]["requiresHumanAcceptance"], False)
        self.assertNotEqual(finding["proposalFingerprint"], old_fp)
        envelope = {"schemaVersion": 1, "reviewKey": artifact["reviewKey"],
                    "decisions": [{"findingId": 101, "status": "APPROVE",
                                   "proposalFingerprint": old_fp}]}
        _, authorized, stale, _ = review_contract.validate_decision_envelope(envelope, updated)
        self.assertEqual(authorized, [])
        self.assertEqual([item["findingId"] for item in stale], [101])

    def _write(self, directory, artifact, patch):
        artifact_path = Path(directory) / "review.json"
        patch_path = Path(directory) / "patch.json"
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        patch_path.write_text(json.dumps(patch), encoding="utf-8")
        return artifact_path, patch_path

    def test_patch_full_analysis_and_recomputes_fingerprint(self):
        finding = make_finding()
        analysis = finding["analysis"]
        finding["analysis"] = None
        finding["proposalFingerprint"] = None
        artifact = make_artifact([finding])
        patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 101, "set": analysis}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            with contextlib.redirect_stdout(io.StringIO()):
                code = review.cmd_patch(ns(
                    artifact=str(artifact_path), patch=str(patch_path)))
            self.assertEqual(code, 0)
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
        updated = data["findings"][0]
        self.assertEqual(updated["analysis"]["assessment"], "CONFIRMED")
        self.assertEqual(
            updated["proposalFingerprint"],
            review_contract.compute_proposal_fingerprint(updated))

    def test_patch_batch_updates_nested_fields(self):
        artifact = make_artifact([make_finding(101), make_finding(102)])
        patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [
                {"id": 101, "set": {"proposal.summary": "new 101"}},
                {"id": 102, "set": {"issueRisk": "high"}},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            with contextlib.redirect_stdout(io.StringIO()):
                code = review.cmd_patch(ns(
                    artifact=str(artifact_path), patch=str(patch_path)))
            self.assertEqual(code, 0)
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
        first, second = data["findings"]
        self.assertEqual(first["analysis"]["proposal"]["summary"], "new 101")
        self.assertEqual(second["analysis"]["issueRisk"], "high")
        self.assertEqual(
            first["proposalFingerprint"],
            review_contract.compute_proposal_fingerprint(first))

    def test_patch_merges_parallel_fragments(self):
        first = make_finding(101)
        second = make_finding(102)
        first_analysis = first["analysis"]
        second_analysis = second["analysis"]
        for finding in (first, second):
            finding["analysis"] = None
            finding["proposalFingerprint"] = None
        artifact = make_artifact([first, second])
        first_patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 101, "set": first_analysis}],
        }
        second_patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 102, "set": second_analysis}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            first_path = Path(directory) / "patch-a.json"
            second_path = Path(directory) / "patch-b.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            first_path.write_text(json.dumps(first_patch), encoding="utf-8")
            second_path.write_text(json.dumps(second_patch), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = review.cmd_patch(ns(
                    artifact=str(artifact_path),
                    patch=[str(first_path), str(second_path)]))
            self.assertEqual(code, 0)
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(
            [finding["analysis"]["assessment"]
                for finding in data["findings"]],
            ["CONFIRMED", "CONFIRMED"])

    def test_patch_rejects_duplicate_ids_across_fragments(self):
        finding = make_finding()
        analysis = finding["analysis"]
        finding["analysis"] = None
        finding["proposalFingerprint"] = None
        artifact = make_artifact([finding])
        fragment = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 101, "set": analysis}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            first_path = Path(directory) / "patch-a.json"
            second_path = Path(directory) / "patch-b.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            first_path.write_text(json.dumps(fragment), encoding="utf-8")
            second_path.write_text(json.dumps(fragment), encoding="utf-8")
            with self.assertRaises(review.ReviewError) as ctx:
                review.cmd_patch(ns(
                    artifact=str(artifact_path),
                    patch=[str(first_path), str(second_path)]))
        self.assertIn("跨 patch 重复", str(ctx.exception))

    def test_patch_rejects_human_decision_fields(self):
        artifact = make_artifact()
        patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 101, "set": {"decision": "APPROVE"}}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            with self.assertRaises(review.ReviewError) as ctx:
                review.cmd_patch(ns(
                    artifact=str(artifact_path), patch=str(patch_path)))
        self.assertIn("人工决策字段", str(ctx.exception))

    def test_patch_strict_rejects_incomplete_analysis(self):
        finding = make_finding()
        finding["analysis"] = None
        finding["proposalFingerprint"] = None
        artifact = make_artifact([finding])
        patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 101, "set": {"assessment": "CONFIRMED"}}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = review.cmd_patch(ns(
                    artifact=str(artifact_path), patch=str(patch_path)))
            self.assertEqual(code, 1)
            self.assertIn("recommendation", err.getvalue())
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertIsNone(data["findings"][0]["analysis"])

    def test_patch_allow_incomplete_writes_partial_analysis(self):
        finding = make_finding()
        finding["analysis"] = None
        finding["proposalFingerprint"] = None
        artifact = make_artifact([finding])
        patch = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "findings": [{"id": 101, "set": {"assessment": "CONFIRMED"}}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = review.cmd_patch(ns(
                    artifact=str(artifact_path), patch=str(patch_path),
                    allow_incomplete=True))
            self.assertEqual(code, 0)
            self.assertIn("允许部分 analysis", buf.getvalue())
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["findings"][0]["analysis"]["assessment"], "CONFIRMED")

    def test_patch_rejects_review_key_mismatch(self):
        artifact = make_artifact()
        patch = {
            "schemaVersion": 1,
            "reviewKey": "other/repo#1",
            "findings": [{"id": 101, "set": {"issueRisk": "low"}}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path, patch_path = self._write(directory, artifact, patch)
            with self.assertRaises(review.ReviewError) as ctx:
                review.cmd_patch(ns(
                    artifact=str(artifact_path), patch=str(patch_path)))
        self.assertIn("reviewKey", str(ctx.exception))


class TestHtmlBuilder(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is needed to execute HTML decision helpers")
    def test_acceptance_uses_explicit_judgment_not_risk_or_keywords(self):
        html = (ROOT / "assets" / "review.html").read_text(encoding="utf-8")
        # Execute the actual pure helper from the shipped template, not a copy.
        helper = re.search(r"^const reviewDefault=.*;$", html, re.M).group(0)
        cases = []
        for issue_risk in ("high", "low"):
            for fix_risk in ("high", "low"):
                for verification in ("无需人工验收", "not manual; no by hand check", "人工确认账号", "截图自动化"):
                    for value in (True, False, None):
                        proposal = {"verification": [verification], "fixRisk": fix_risk}
                        if value is not None:
                            proposal["requiresHumanAcceptance"] = value
                        cases.append({"finding": {"analysis": {"issueRisk": issue_risk, "proposal": proposal}},
                                      "expected": value is not False})
        program = helper + "\nconst cases=JSON.parse(require('fs').readFileSync(0,'utf8'));\n" + (
            "for(const c of cases)if(reviewDefault(c.finding)!==c.expected)throw Error(JSON.stringify(c));")
        result = subprocess.run([shutil.which("node"), "-e", program],
                                input=json.dumps(cases), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_html_escapes_script_breakout(self):
        malicious = "</script><script>alert(1)</script> & < >"
        finding = make_finding()
        finding["source"]["note"] = malicious
        artifact = make_artifact([finding])
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            out = Path(directory) / "review.html"
            artifact_path.write_text(
                json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            html_path, _ = review_html.build_html(artifact_path, out)
            html = html_path.read_text(encoding="utf-8")
        self.assertNotIn(malicious, html)
        self.assertIn("\\u003c/script\\u003e", html)
        match = re.search(
            r'<script type="application/json" id="review-data">(.*?)</script>',
            html, re.S)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["findings"][0]["source"]["note"], malicious)

    def test_build_html_with_closed_only(self):
        artifact = make_artifact([])
        artifact["closedFindings"] = [make_closed_finding()]
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            out = Path(directory) / "review.html"
            artifact_path.write_text(
                json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            html_path, _ = review_html.build_html(artifact_path, out)
            html = html_path.read_text(encoding="utf-8")
        self.assertIn('queue-closed', html)
        self.assertIn("已关闭 · 无需决策", html)

    def test_build_html_rejects_incomplete_analysis(self):
        finding = make_finding()
        finding["analysis"] = None
        finding["proposalFingerprint"] = None
        artifact = make_artifact([finding])
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            artifact_path.write_text(
                json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(review_html.BuildError) as ctx:
                review_html.build_html(artifact_path)
        self.assertIn("analysis", str(ctx.exception))

    def test_safe_json_for_script_roundtrips(self):
        value = {"note": "</script> & < >"}
        encoded = review_html.safe_json_for_script(value)
        self.assertIn("\\u003c", encoded)
        self.assertEqual(json.loads(encoded), value)


class TestCheckEnvelope(unittest.TestCase):
    def test_check_envelope_valid(self):
        artifact = make_artifact([make_finding(101), make_finding(102)])
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "artifactPath": artifact["artifactPath"],
            "decisions": [
                {"findingId": 101,
                 "proposalFingerprint": artifact["findings"][0]["proposalFingerprint"],
                 "status": "APPROVE"},
                {"findingId": 102,
                 "proposalFingerprint": artifact["findings"][1]["proposalFingerprint"],
                 "status": "CLOSE", "note": "误报，已确认不适用"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            envelope_path = Path(directory) / "envelope.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = review.cmd_check_envelope(ns(
                    artifact=str(artifact_path), envelope=str(envelope_path)))
        self.assertEqual(code, 0)
        self.assertIn("authorized=2", buf.getvalue())

    def test_check_envelope_reports_missing_status_without_crashing(self):
        artifact = make_artifact()
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [{"findingId": 101}],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            envelope_path = Path(directory) / "envelope.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = review.cmd_check_envelope(ns(
                    artifact=str(artifact_path), envelope=str(envelope_path)))
        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("invalid=1", output)
        self.assertIn("INVALID     101", output)
        self.assertIn("MISSING=1", output)

    def test_check_envelope_stale_does_not_block_other_findings(self):
        artifact = make_artifact([make_finding(101), make_finding(102)])
        envelope = {
            "schemaVersion": 1,
            "reviewKey": artifact["reviewKey"],
            "decisions": [
                {"findingId": 101,
                 "proposalFingerprint": "deadbeef",
                 "status": "APPROVE"},
                {"findingId": 102,
                 "proposalFingerprint": artifact["findings"][1]["proposalFingerprint"],
                 "status": "APPROVE"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "review.json"
            envelope_path = Path(directory) / "envelope.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
            buf = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                code = review.cmd_check_envelope(ns(
                    artifact=str(artifact_path), envelope=str(envelope_path)))
        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("authorized=1", output)
        self.assertIn("stale=1", output)
        self.assertIn("AUTHORIZED  102", output)
        self.assertIn("STALE       101", output)
        self.assertIn("PARTIAL", output)
        self.assertEqual(err.getvalue(), "")




class TestEnvelopeNonExecutingStatuses(unittest.TestCase):
    """DEFER / PROVIDE_INFO 是有效决策但非执行授权；PROVIDE_INFO 缺输入判 INVALID。"""

    def _finding(self):
        proposal = {
            "summary": "s", "approach": "a", "files": ["f.ts"],
            "verification": ["npm test"], "fixRisk": "low",
        }
        finding = {
            "id": 1,
            "source": {"path": "f.ts", "note": "n", "author": "a"},
            "analysis": {"recommendation": "FIX", "assessment": "CONFIRMED",
                         "issueRisk": "low", "proposal": proposal},
        }
        finding["proposalFingerprint"] = review_contract.compute_proposal_fingerprint(finding)
        return finding

    def _envelope(self, status, **extra):
        finding = self._finding()
        return ({"reviewKey": "k", "findings": [finding]},
                {"schemaVersion": 1, "reviewKey": "k", "decisions": [
                    {"findingId": 1, "proposalFingerprint": finding["proposalFingerprint"],
                     "status": status, **extra}]})

    def test_defer_valid_but_not_authorized(self):
        artifact, envelope = self._envelope("DEFER", note="本 MR 不处理")
        errors, authorized, stale, invalid = review_contract.validate_decision_envelope(envelope, artifact)
        self.assertEqual((errors, authorized, stale, invalid), ([], [], [], []))

    def test_provide_info_with_note_valid_not_authorized(self):
        artifact, envelope = self._envelope("PROVIDE_INFO", note="后端白名单校验")
        errors, authorized, stale, invalid = review_contract.validate_decision_envelope(envelope, artifact)
        self.assertEqual((errors, authorized, stale, invalid), ([], [], [], []))

    def test_provide_info_without_input_invalid(self):
        artifact, envelope = self._envelope("PROVIDE_INFO")
        errors, authorized, stale, invalid = review_contract.validate_decision_envelope(envelope, artifact)
        self.assertEqual((authorized, stale), ([], []))
        self.assertEqual(len(invalid), 1)
        self.assertIn("PROVIDE_INFO", invalid[0]["reason"])

    def test_provide_info_with_answers_only_valid(self):
        artifact, envelope = self._envelope("PROVIDE_INFO", answers={"0": "白名单在后端"})
        errors, authorized, stale, invalid = review_contract.validate_decision_envelope(envelope, artifact)
        self.assertEqual((errors, authorized, stale, invalid), ([], [], [], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
