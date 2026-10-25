#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Review Artifact 与 Decision Envelope 的确定性契约。

只负责枚举、稳定 Key、指纹和结构校验；不判断 finding 是否成立，
也不决定人工应该如何选择。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = 1

ASSESSMENTS = ("CONFIRMED", "DISMISSED", "NEEDS_EVIDENCE")
RECOMMENDATIONS = ("FIX", "DISMISS", "DEFER", "NEEDS_EVIDENCE")
DECISION_STATUSES = ("APPROVE", "CLOSE", "DEFER", "PROVIDE_INFO", "UNDECIDED")
RISKS = ("high", "medium", "low")
PLATFORM_INTERPRETATIONS = (
    "PENDING",
    "CLOSED_NOT_ADOPTED",
    "IGNORED",
    "CLOSED_WITH_ACTION",
    "UNKNOWN",
)
ASSESSMENT_RECOMMENDATIONS = {
    "CONFIRMED": {"FIX", "DEFER"},
    "DISMISSED": {"DISMISS"},
    "NEEDS_EVIDENCE": {"NEEDS_EVIDENCE"},
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_review_key(repo: str, merge_request_id: int) -> str:
    """Review Key 只关联 repo + 项目级 MR id，不随评论变化。"""
    return f"{repo}#{int(merge_request_id)}"


def compute_proposal_fingerprint(finding: dict) -> str:
    """覆盖会影响授权语义的分析内容。

    包含 assessment / recommendation / issueRisk / trigger / impact / rootCause /
    evidence / openQuestions / proposal，因此问题是否成立、根因或证据变化、
    方案或修复风险变化都会让旧授权失效。
    不覆盖 source.note、行号、diff 快照、平台状态或 updatedAt。
    """
    analysis = finding.get("analysis")
    if not isinstance(analysis, dict):
        return ""
    proposal = analysis.get("proposal")
    if not isinstance(proposal, dict):
        proposal = {}
    payload = {
        "assessment": analysis.get("assessment"),
        "recommendation": analysis.get("recommendation"),
        "issueRisk": analysis.get("issueRisk"),
        "trigger": analysis.get("trigger"),
        "impact": analysis.get("impact"),
        "rootCause": analysis.get("rootCause"),
        "evidence": analysis.get("evidence") or [],
        "openQuestions": analysis.get("openQuestions") or [],
        "proposal": proposal,
    }
    digest = hashlib.sha256(canonical_json(
        payload).encode("utf-8")).hexdigest()
    return digest[:16]


def platform_interpretation(adopted, closed) -> str:
    """把平台原始 adopted / closed 映射成唯一的处置解释。

    CLI / Artifact / HTML 都只消费本函数的结果，不再各自解读 adopted/closed。
    - `IGNORED` 只在 `closed == 1 且 adopted == 3` 这一**已观测组合**上返回
      （目标平台单 MR 观测：UI 显示“已忽略”）。它只是平台的处置动作，
      不代表问题成立 / 误报 / 已修复。
    - `adopted == 2 / 4` 等取值缺样本，一律落 `CLOSED_WITH_ACTION`（已知已处理、
      未知具体动作），不猜测其语义。
    """
    if adopted == 1 and closed == 0:
        return "PENDING"
    if closed == 1 and adopted == 0:
        return "CLOSED_NOT_ADOPTED"
    if closed == 1 and adopted == 3:
        return "IGNORED"
    if closed == 1 and adopted is not None:
        return "CLOSED_WITH_ACTION"
    return "UNKNOWN"


def _non_empty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_answers(value) -> bool:
    """answers 为对象且至少一个非空字符串值。"""
    if not isinstance(value, dict):
        return False
    return any(isinstance(v, str) and v.strip() for v in value.values())


def _string_list(value) -> bool:
    return (isinstance(value, list)
            and bool(value)
            and all(_non_empty(item) for item in value))


def _validate_analysis(prefix: str, analysis: dict, errors: list[str]) -> None:
    assessment = analysis.get("assessment")
    recommendation = analysis.get("recommendation")
    if assessment not in ASSESSMENTS:
        errors.append(f"{prefix}.assessment 无效：{assessment!r}")
        return
    if recommendation not in RECOMMENDATIONS:
        errors.append(f"{prefix}.recommendation 无效：{recommendation!r}")
        return
    if recommendation not in ASSESSMENT_RECOMMENDATIONS[assessment]:
        errors.append(
            f"{prefix}.recommendation {recommendation} 与 "
            f"assessment {assessment} 不一致")
    if analysis.get("issueRisk") not in RISKS:
        errors.append(f"{prefix}.issueRisk 无效：{analysis.get('issueRisk')!r}")
    for key in ("trigger", "impact"):
        if not _non_empty(analysis.get(key)):
            errors.append(f"{prefix}.{key} 不能为空")
    if assessment == "CONFIRMED" and not _non_empty(analysis.get("rootCause")):
        errors.append(f"{prefix}.rootCause 在 CONFIRMED 时不能为空")

    evidence = analysis.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{prefix}.evidence 至少需要一条")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"{prefix}.evidence[{index}] 必须是对象")
                continue
            if item.get("kind") not in ("OBSERVED", "DERIVED", "INFERRED"):
                errors.append(
                    f"{prefix}.evidence[{index}].kind 无效：{item.get('kind')!r}")
            for key in ("ref", "summary"):
                if not _non_empty(item.get(key)):
                    errors.append(f"{prefix}.evidence[{index}].{key} 不能为空")

    open_questions = analysis.get("openQuestions")
    if not isinstance(open_questions, list):
        errors.append(f"{prefix}.openQuestions 必须是数组")
        open_questions = []
    if assessment == "NEEDS_EVIDENCE" and not open_questions:
        errors.append(f"{prefix}.openQuestions 在 NEEDS_EVIDENCE 时不能为空")

    if recommendation == "FIX":
        proposal = analysis.get("proposal")
        if not isinstance(proposal, dict):
            errors.append(f"{prefix}.proposal 在 FIX 时不能为空")
            return
        if not _non_empty(proposal.get("summary")):
            errors.append(f"{prefix}.proposal.summary 不能为空")
        if not _non_empty(proposal.get("approach")):
            errors.append(f"{prefix}.proposal.approach 不能为空")
        if not _string_list(proposal.get("files")):
            errors.append(f"{prefix}.proposal.files 至少需要一个文件")
        if not _string_list(proposal.get("verification")):
            errors.append(f"{prefix}.proposal.verification 至少需要一项")
        if proposal.get("fixRisk") not in RISKS:
            errors.append(f"{prefix}.proposal.fixRisk 无效")
        if ("requiresHumanAcceptance" in proposal
                and not isinstance(proposal["requiresHumanAcceptance"], bool)):
            errors.append(f"{prefix}.proposal.requiresHumanAcceptance 必须是布尔值")
    elif recommendation in ("DISMISS", "DEFER"):
        proposal = analysis.get("proposal")
        if proposal is not None and not isinstance(proposal, dict):
            errors.append(f"{prefix}.proposal 必须是对象或 null")


def validate_finding_analysis(finding: dict, require_analysis: bool = True,
                              prefix: str = "finding") -> list[str]:
    """校验单个 finding 的 analysis 与指纹；供 artifact 和 patch 复用。"""
    errors: list[str] = []
    analysis = finding.get("analysis")
    if analysis is None:
        if require_analysis:
            errors.append(f"{prefix}.analysis 不能为空")
        return errors
    if not isinstance(analysis, dict):
        return [f"{prefix}.analysis 必须是对象或 null"]
    _validate_analysis(prefix, analysis, errors)
    expected = compute_proposal_fingerprint(finding)
    if finding.get("proposalFingerprint") != expected:
        errors.append(
            f"{prefix}.proposalFingerprint 与当前 analysis 不一致；"
            "请重新计算后再交给 HTML/Agent")
    return errors


def _validate_source(prefix: str, source, errors: list[str]) -> None:
    if not isinstance(source, dict):
        errors.append(f"{prefix}.source 必须是对象")
        return
    for key in ("note", "path"):
        if not isinstance(source.get(key), str):
            errors.append(f"{prefix}.source.{key} 必须是字符串")
    for key in ("category", "severity", "severityLabel", "title"):
        if key in source and not isinstance(source[key], str):
            errors.append(f"{prefix}.source.{key} 必须是字符串")
    interpretation = source.get("platformInterpretation")
    if interpretation is not None and interpretation not in PLATFORM_INTERPRETATIONS:
        errors.append(
            f"{prefix}.source.platformInterpretation 无效："
            f"{interpretation!r}")
    platform = source.get("platform")
    if isinstance(platform, dict):
        expected = platform_interpretation(
            platform.get("adopted"), platform.get("closed"))
        if interpretation is not None and interpretation != expected:
            errors.append(
                f"{prefix}.source.platformInterpretation {interpretation} "
                f"与平台字段不一致，应为 {expected}")


def validate_review_artifact(data: dict, require_analysis: bool = True) -> list[str]:
    """返回全部结构错误；不判断根因或方案是否合理。"""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["artifact 必须是 JSON 对象"]
    if data.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(
            f"schemaVersion 必须是 {SCHEMA_VERSION}，"
            f"当前是 {data.get('schemaVersion')!r}")
    repo = data.get("repo")
    merge_request_id = data.get("mergeRequestId")
    if not _non_empty(repo) or "/" not in repo:
        errors.append("repo 必须是 foo/bar 形式")
    if not isinstance(merge_request_id, int) or isinstance(merge_request_id, bool):
        errors.append("mergeRequestId 必须是整数")
    if (_non_empty(repo) and isinstance(merge_request_id, int)
            and data.get("reviewKey") != compute_review_key(repo, merge_request_id)):
        errors.append("reviewKey 与 repo + mergeRequestId 不一致")
    if not _non_empty(data.get("artifactPath")):
        errors.append("artifactPath 不能为空")
    if not isinstance(data.get("headMatches"), (bool, type(None))):
        errors.append("headMatches 必须是布尔值或 null")
    selection = data.get("selection")
    if selection is not None:
        if not isinstance(selection, dict):
            errors.append("selection 必须是对象")
        else:
            mode = selection.get("mode")
            if mode not in ("all", "ids"):
                errors.append(f"selection.mode 无效：{mode!r}")
            requested_ids = selection.get("requestedIds")
            if not isinstance(requested_ids, list) or not all(
                    isinstance(item, int) and not isinstance(item, bool)
                    for item in requested_ids):
                errors.append("selection.requestedIds 必须是整数数组")
            elif mode == "ids" and not requested_ids:
                errors.append("selection.mode=ids 时 requestedIds 不能为空")

    findings = data.get("findings")
    closed = data.get("closedFindings", [])
    if closed is None:
        closed = []
    if not isinstance(closed, list):
        errors.append("closedFindings 必须是数组")
        closed = []
    if not isinstance(findings, list):
        errors.append("findings 必须是数组")
        return errors
    if not findings and not closed:
        errors.append("findings 与 closedFindings 至少有一个非空")
        return errors

    seen: set[int] = set()
    for index, finding in enumerate(findings):
        prefix = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        finding_id = finding.get("id")
        if not isinstance(finding_id, int) or isinstance(finding_id, bool):
            errors.append(f"{prefix}.id 必须是整数")
        elif finding_id in seen:
            errors.append(f"{prefix}.id 重复：{finding_id}")
        else:
            seen.add(finding_id)

        _validate_source(prefix, finding.get("source"), errors)

        analysis = finding.get("analysis")
        if analysis is None:
            if require_analysis:
                errors.append(f"{prefix}.analysis 不能为空")
            continue
        if not isinstance(analysis, dict):
            errors.append(f"{prefix}.analysis 必须是对象或 null")
            continue
        errors.extend(validate_finding_analysis(
            finding, require_analysis=require_analysis, prefix=prefix))

    for index, finding in enumerate(closed):
        prefix = f"closedFindings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        finding_id = finding.get("id")
        if not isinstance(finding_id, int) or isinstance(finding_id, bool):
            errors.append(f"{prefix}.id 必须是整数")
        elif finding_id in seen:
            errors.append(f"{prefix}.id 重复：{finding_id}")
        else:
            seen.add(finding_id)
        _validate_source(prefix, finding.get("source"), errors)
        if finding.get("analysis") is not None:
            errors.append(f"{prefix}.analysis 必须为空；closed 只汇报，不分析")
    return errors


def _has_executable_proposal(finding: dict) -> bool:
    analysis = finding.get("analysis")
    if not isinstance(analysis, dict):
        return False
    proposal = analysis.get("proposal")
    if not isinstance(proposal, dict):
        return False
    return (
        _non_empty(proposal.get("summary"))
        and _non_empty(proposal.get("approach"))
        and _string_list(proposal.get("files"))
        and _string_list(proposal.get("verification"))
        and proposal.get("fixRisk") in RISKS
    )


def validate_decision_envelope(envelope: dict, artifact: dict) -> tuple[
        list[str], list[int], list[dict], list[dict]]:
    """返回 (全局错误, authorized, stale, invalid)。

    stale / invalid 都是单条 Finding 的状态，不阻止其他 Finding 执行。
    """
    errors: list[str] = []
    authorized: list[int] = []
    stale: list[dict] = []
    invalid: list[dict] = []
    if not isinstance(envelope, dict):
        return ["Decision Envelope 必须是 JSON 对象"], authorized, stale, invalid
    if envelope.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"Decision Envelope schemaVersion 必须是 {SCHEMA_VERSION}")
    if envelope.get("reviewKey") != artifact.get("reviewKey"):
        errors.append("Decision Envelope 的 reviewKey 与 artifact 不一致")

    findings = artifact.get("findings")
    if not isinstance(findings, list):
        return errors + ["artifact.findings 必须是数组"], authorized, stale, invalid
    by_id = {finding.get("id"): finding for finding in findings
             if isinstance(finding, dict)}

    decisions = envelope.get("decisions")
    if not isinstance(decisions, list):
        return errors + ["Decision Envelope.decisions 必须是数组"], authorized, stale, invalid

    seen: set[int] = set()
    for index, decision in enumerate(decisions):
        prefix = f"decisions[{index}]"
        if not isinstance(decision, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        finding_id = decision.get("findingId")
        if not isinstance(finding_id, int) or isinstance(finding_id, bool):
            errors.append(f"{prefix}.findingId 必须是整数")
            continue
        if finding_id in seen:
            errors.append(f"{prefix}.findingId 重复：{finding_id}")
            continue
        seen.add(finding_id)

        status = decision.get("status")
        if status not in DECISION_STATUSES:
            invalid.append({
                "findingId": finding_id,
                "reason": f"未知决策状态：{status!r}",
            })
            continue
        finding = by_id.get(finding_id)
        if not isinstance(finding, dict):
            invalid.append({
                "findingId": finding_id,
                "reason": "该 finding 不在 artifact 中",
            })
            continue
        if status == "UNDECIDED":
            # 未授权（初始态 / stale / invalid 降级），不是错误，也不执行。
            continue

        expected = compute_proposal_fingerprint(finding)
        if (not decision.get("proposalFingerprint")
                or decision.get("proposalFingerprint") != expected):
            stale.append({
                "findingId": finding_id,
                "reason": "proposalFingerprint 缺失或已过期",
            })
            continue
        if status in ("DEFER", "PROVIDE_INFO"):
            # 有效但非执行类决策：暂缓 / 提交补充信息待重评，不进入执行授权。
            if status == "PROVIDE_INFO" and not (
                    _non_empty(decision.get("note"))
                    or _non_empty_answers(decision.get("answers"))):
                invalid.append({
                    "findingId": finding_id,
                    "reason": "PROVIDE_INFO 需要补充信息（note 或 answers）",
                })
                continue
            continue
        if status == "APPROVE":
            analysis = finding.get("analysis")
            if (not isinstance(analysis, dict)
                    or analysis.get("recommendation") != "FIX"
                    or not _has_executable_proposal(finding)):
                invalid.append({
                    "findingId": finding_id,
                    "reason": "APPROVE 需要有效的 FIX 方案",
                })
                continue
            proposal = analysis["proposal"]
            expected_acceptance = proposal.get("requiresHumanAcceptance", True)
            # 旧 artifact / envelope 可恢复；缺字段不表示自动验证充分。
            # 新方案必须携带与指纹绑定的判断，不能在 envelope 中降级。
            if ("requiresHumanAcceptance" in decision
                    or "requiresHumanAcceptance" in proposal):
                acceptance = decision.get("requiresHumanAcceptance")
                if (not isinstance(acceptance, bool)
                        or acceptance != expected_acceptance):
                    invalid.append({
                        "findingId": finding_id,
                        "reason": "requiresHumanAcceptance 缺失或与方案不一致",
                    })
                    continue
        if status == "CLOSE":
            if not _non_empty(decision.get("note")):
                invalid.append({
                    "findingId": finding_id,
                    "reason": "CLOSE 必须填写理由（note）",
                })
                continue
        authorized.append(finding_id)
    return errors, authorized, stale, invalid
