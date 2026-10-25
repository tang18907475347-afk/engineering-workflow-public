# Implementation Spec — <Spec Target Scope>

<!-- 实现规格（Replica-Ready 交付物）。可承载完整开发级语义，但每个重要结论必须可追溯到 canonical E-* / C-* / J-* / B-*。
     行为完整性以 B-* 为单位，不以 Inventory 条目为终点；Inventory 只回答发现了哪些能力/入口/对象/依赖。
     不新增 Feature Registry。小 Scope 可用本文件承载全部节；大 Scope 可拆分为家族文件，本文件作为 INDEX。
     只保留适用节；不适用写 N/A + 理由或删除，不为“完整”补空表。
     Evidence 变化后必须重新核对并更新受影响节；不声称自动重生。 -->

## Spec Target Scope

<!-- Spec Target Scope = 独立 Coding Agent 需要重建的范围，由本文件签发。
     Baseline Scope = 本次系统现实调查覆盖的范围，由 BASELINE_INDEX.md 签发。
     调查范围可以大于复刻范围；两者不要求相等。本文件必须引用 Baseline Scope（若存在）并声明关系。 -->

- Scope type: `chain / module / domain / system`
- Target:
- Relation to Baseline Scope: `equal / subset / diverged`（diverged 时说明原因）
- Baseline Scope ref: `BASELINE_INDEX.md`（若存在）
- In-scope capabilities / Inventory items:
- Out-of-scope (explicit):
- Evidence boundary:

## Dependencies & Boundaries

<!-- 只写对目标行为有影响的契约，不写依赖内部全部功能。Relation=dependency 的 Inventory 项在此汇总。 -->

| Dependency | Relation | Contract (interface / I/O / state / failure / precondition / assumption) | Evidence refs |
| ---------- | -------- | ------------------------------------------------------------------------ | ------------- |

## Behavior Contracts

<!-- 每个 in-scope Inventory item 的相关 B-* 必须列出；每个 B-* 的条件、状态、分支、副作用与异常路径进入本表。
     Inventory COVERED 不等于行为契约已恢复。不新增 Feature Registry。 -->

| Inventory Item | B-ID | Contract (conditions / states / branches / side effects) | Spec section | Evidence refs |
| -------------- | ---- | -------------------------------------------------------- | ------------ | ------------- |

## System-Level Behavior

<!-- 仅当 Spec Target Scope 包含 backend / async / stateful 能力时填写；不适用写 N/A + 理由。
     这些是 B-* 的系统级补充，不是新 registry。 -->

| B-ID | Concurrency / race | Idempotency / duplicate | Ordering | Timeout / retry / backoff | Partial failure / compensation | Dependency degradation | Evidence refs |
| ---- | ------------------ | ----------------------- | -------- | ------------------------- | ------------------------------ | ---------------------- | ------------- |

## Interfaces

| Interface | Method / Route / Event | Input | Output | Errors | Evidence refs |
| --------- | ---------------------- | ----- | ------ | ------ | ------------- |

## Data Model

| Entity / Field | Type | Constraints | Lifecycle | Evidence refs |
| -------------- | ---- | ----------- | --------- | ------------- |

## State Machines

| Object | States | Transitions (trigger → guard → effect) | Evidence refs |
| ------ | ------ | -------------------------------------- | ------------- |

## Permissions & Preconditions

| Capability | Required permission / precondition | Failure behavior | Evidence refs |
| ---------- | ---------------------------------- | ---------------- | ------------- |

## Validations & Error Handling

| Input / Action | Validation rule | Error / feedback | Evidence refs |
| -------------- | --------------- | ---------------- | ------------- |

## Background Jobs & Side Effects

| Job / Side effect | Trigger | Input / Output | Failure / retry | Evidence refs |
| ----------------- | ------- | -------------- | --------------- | ------------- |

## Integrations

| External system | Purpose | Interface / contract | Failure mode | Evidence refs |
| --------------- | ------- | -------------------- | ------------ | ------------- |

## Acceptance Criteria

<!-- 唯一 acceptance 来源；按 B-* 组织，每个 B-* 至少一条可独立验证的验收条件。
     这是规格充分性的语义判断，由模型决定，不由 validator 强制。 -->

| B-ID | Inventory Item | Acceptance criterion | Verification method |
| ---- | -------------- | -------------------- | ------------------- |

## Unknowns & Blockers

<!-- 引用 Unknown Registry (U-*)。replication-blocking = 影响 in-scope 行为契约或 dependency contract。 -->

| U-ID | B-ID / Inventory Item | Item | Impact | Replication-blocking? | Status |
| ---- | --------------------- | ---- | ------ | --------------------- | ------ |

## Replica-Ready Judgment

<!-- 单一判断来源：只有本文件签发 Replica-Ready Judgment；BASELINE_INDEX.md 只引用。
     Spec Target Scope / Baseline Scope relation 与 Evidence boundary 只在 `## Spec Target Scope` 声明，本节不重复。 -->

- Replica-Ready: `是 / 否`
- Blockers (引用 `U-*`):
- 不承诺无损源码重建；本规格支持独立开发功能与行为高度相似的新系统。
