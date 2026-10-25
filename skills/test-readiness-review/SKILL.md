---
name: test-readiness-review
description: 在用户明确要求判断当前 Requirement 是否可以提测、是否达到 READY_FOR_TEST，或要求独立交付审查时使用。不用于需求澄清、工程方案设计、代码实现、QA 测试管理或缺陷单据单独修复。
---

# Test Readiness Review

## Runtime Contract
- **Outcome**：独立确认当前交付的 Expected、Actual、Preserved、Proven 是否闭环。
- **Done**：已确认需求完整落地、实际改动未越界、应保持行为未被破坏、开发侧必要结论已有足够证据。
- **Next consumer**：`READY_FOR_TEST` → QA；`BLOCK` → 原实现上下文修复后，在 fresh context 重新 Review。
- **Stop**：只审查和裁决；不重新澄清需求、重新设计方案、直接修改代码、修改 Workspace 或代替 QA。

这个 Skill 是独立的交付审查能力，不是 Implementation Strategy 的另一个执行模式，也不是新的持久状态或生命周期阶段。Implementation Strategy 内部的 Completion Review 负责实施侧 Workspace Reconciliation；本 Skill 消费完成后的产物，提供独立的第二次判断。

## Applicability and Scope
当前版本只审查 Requirement 交付，不接管独立缺陷修复。缺陷单据的采集、分析、修复和回写继续由 `bugfix` 按自己的档案与验证契约处理。MR 上的外部 AI 评审意见由 `ai-code-review` 逐条处理；本 Skill 不逐条裁决评论，只判断 Requirement 是否能提测。

Requirement scope 按以下顺序解析：用户显式指定的 requirement slug > 当前输入中唯一可推导的 requirement slug > 无法唯一确定 → BLOCK，并说明需要的 scope。

禁止依赖全局「current requirement」。本次 Review 至少按需读取：

- `.engineering/requirements/<requirement-slug>/clarification/`
- `.engineering/requirements/<requirement-slug>/workspace/`
- `.engineering/design/`（相关设计决定 / handoff，设计驱动交付时）
- `.engineering/product/`（相关 Current Reality，按需）
- Current Repo / 当前 worktree
- Current Git Diff
- 可用的测试、runtime、visual evidence

缺少的 artifact 只有在它会阻止形成 Expected Contract 或验证关键结论时才构成 BLOCK；不得用 README、历史对话或实现者自述补成不存在的 canonical artifact。**没有 Clarification、没有 Baseline 或没有 Handoff 本身不是 BLOCK**：从当前有效的用户输入、已接受设计决定、PRD / 设计稿、Current Repo 与 Diff 形成 Expected。**Requirement 内由 Product Design 直接完成的局部设计 + 实现也可以作为审查对象**：Expected 来自已接受设计决定、Clarification（如有）与 Current Diff；没有 Requirement Workspace 本身不是 BLOCK。

### Diff 基线
- 优先检查当前 worktree 的 staged 与 unstaged diff。
- 如果 worktree 干净，必须有用户或任务明确提供的 commit、base ref 或交付范围才能审查已提交改动。
- 不默认把 `HEAD~1` 当作交付范围，不猜测本次改动。
- 无法确定 Actual 的交付边界时，直接 BLOCK。

## Authority
|判断对象|Authority|
|---|---|
|用户最终应该得到什么行为|当前有效的用户输入 / Clarification / 已接受设计决定（`ACCEPTED`）|
|工程上应如何落地、改什么、保留什么|Requirement Workspace；没有 Workspace 的局部设计实现，用已接受设计决定 + 任务输入 + Current Diff|
|当前系统真实实现|Current Repo|
|本次实际修改|Current Git Diff|
|已经被证明的结果|Tests / Runtime / Visual Evidence|
|历史代码机制认知|代码机制缓存，仅作为按需探索|

冲突处理：
|情况|处理|
|---|---|
|Clarification 存在且与 Workspace 冲突|BLOCK：产品语义与工程指导冲突，不自行选边|
|没有 Clarification，但有已接受 Design 决定|以 ACCEPTED 决定与 Binding handoff 形成 Expected；PROPOSED 设计不当作已接受要求|
|Workspace ≠ Current Repo|以 Repo 作为当前工程事实；判断 Workspace stale 或实现偏离|
|代码机制缓存 ≠ Current Repo|Repo 胜；按缓存契约修正或删除 stale fact|

Review 不能把实现者在 Workspace、提交说明或历史对话里的“已完成”当作证据。结论强度不得超过当前可复核证据。

## Reference routing
|当前问题|读|
|---|---|
|Workspace 路径、ownership 或写入边界有疑问|[references/workspace-and-ownership.md](references/workspace-and-ownership.md)|
|事实冲突、旧结论失效，需要判断证据是否仍有效|[references/evidence-and-correction.md](references/evidence-and-correction.md)|
|涉及决定状态、Binding 或 handoff 消费|[references/delivery-and-handoff.md](references/delivery-and-handoff.md)|

## Review Workflow

### 1. Build the Expected Contract
只从当前有效的用户输入、Clarification、Workspace、已接受 Design 决定与 Binding handoff、PRD / 设计稿中提取已经确认、且会影响交付判断的内容，形成本次会话内的临时 Expected Contract：Behavior Delta / Acceptance、Interaction Delta、Engineering Delta、Preserve、Verification Obligation。

设计驱动交付时，`design/module-handoffs/<module-id>/<handoff-id>.md` 的 `Binding` 是 Expected 的来源；`Adjustable` 中的 `PROPOSED` 不是已接受要求，除非它被当前交付明确采纳并记录。消费者记录实际消费的 handoff-id；若 handoff 被 supersede，只重新检查与当前交付相关的部分。**Review 期间发现新的、此前未被引用的关键事实时，也要检查它是否影响当前 Expected；不能因为旧 handoff 没有引用它而忽略。**

这份 Contract 只用于本次 Review：不新增 artifact、不建立新 schema、不持久化第二份 requirement truth、不重新解释或扩写需求。如果当前有效输入无法形成唯一的产品行为、工程边界或完成证据要求，BLOCK，并指出缺少的决策或 artifact。没有 Clarification / Baseline / Handoff 时，不等于无法形成 Expected；直接从可用来源形成即可。

### 2. Trace Every Confirmed Delta
对每一项 confirmed delta 临时追踪：Confirmed Requirement → Expected Behavior → Implementation Anchor → Verification Evidence。

每项只能得到以下状态：Implemented + Proven / Implemented + Unproven / Missing / Incorrect / Unintended。

confirmed behavior 缺失、实现不一致、未确认的产品语义被固化、开发侧必须提供的证据缺失，都会形成 BLOCK。

### 3. Close the Interaction State
对关键用户路径按完整链路检查：User Action → Pending / Immediate State → Success / Failure → Persistent State → Next Available Action。

只检查影响交付判断的行为：loading、success、error、empty、disabled/enabled、submit、retry、cancel、back、refresh、输入保留、同步结果、失败恢复、返回/刷新/再次进入后的行为，以及 Clarification 已确认的交互结果。不能证明状态闭环、用户输入丢失、失败无恢复路径，或 UI state 与真实 data state 不一致时，BLOCK。

### 4. Check Engineering Conformance
对照 Workspace 的 Engineering Delta 与 Current Diff 检查：

- change boundary 是否完整覆盖；
- owner、writer、dataflow 是否落在正确位置；
- 是否漏改必要 owner 或改到错误 owner；
- 是否存在明显无关扩散；
- 是否违反 Current Repo invariant；
- 是否有直接影响 runtime correctness 的问题。

普通 symbol、单文件事实和 caller/consumer 列表直接读源码。只有遇到符合缓存准入条件的高成本跨文件 owner/dataflow 问题时，才按需查 `.engineering/intelligence/`；命中后仍回到 Current Repo 核验。

### 5. Check Preserved Behavior
Preserve 是独立的一等对象。只从 Workspace 的 Preserve 与 Actual Diff 出发，扫描本次实际触碰到、且明确不应改变的既有行为：Changed Owner / State / Dataflow → Which preserved behavior can be affected? → Did Actual change it? → Is there sufficient evidence it still holds?

重点检查 shared owner、default behavior、fallback、error、empty 和已有用户路径是否被新行为覆盖。若改动触碰共享行为，而现有材料不足以判断 Preserve 是否成立，且该判断会影响是否进 QA，BLOCK。不要把检查扩成全仓 blast-radius audit。

### 6. Check Actual - Expected
主动检查实现有没有多做会改变产品或系统行为的事情，例如：

- 把局部状态变化提升成全局权限变化；
- 将局部入口改成公共组件默认行为；
- 把 Workspace 指定的局部 owner 提升到共享层并影响其他消费者；
- 增加未经确认的自动行为、默认值、跳转、数据写入或状态转换。

只有实际行为变化才报告；纯实现细节变化不属于 unintended behavior。

### 7. Detect Cross-artifact Contradictions
主动寻找：

- Clarification says A / Workspace says B
- Workspace says modify X / Diff actually modifies Y
- Workspace says preserve C / Actual changes C
- Verification says D proven / Evidence never exercises D

影响交付判断的跨层矛盾一律 BLOCK，不自行选择“更合理”的版本。

### 8. Prove the Required Claims
对每个 Expected / Verification Obligation 回答四件事：Expected → Evidence Required（证明它至少需要什么证据类型）→ Evidence Available（实际拿到什么、来源 / 范围 / 可重放性）→ Proven（这些证据实际证明了哪一部分）。

证据类型可以包括 source / code、deterministic test、DOM、interaction、visual、runtime、data-snapshot 等；它们是**证据要求**，不是验证结果，也不与任何 `PASS` 标签建立一一映射。

设计侧记录 `PASS — CODE / DOM / INTERACTION / VISUAL / NOT VERIFIED` 时，这些是**证据描述**：`PASS — INTERACTION` 只说明实际交互路径被验证过，不说明所有状态、入口或视觉保真；`PASS — VISUAL` 只说明在给定视口/环境下视觉成立。它们可以作为 `Evidence Available` 输入，但不能直接当作 TRR 的 `Proven` 结论；TRR 独立判断证据是否覆盖当前 Expected。

测试命令成功、代码“看起来合理”、孤立单测通过、实现者自述或设计侧 `PASS` 标签，都不能自动证明未被覆盖的 claim。如果缺证据的项明确属于 QA ownership，可以进入 QA Handoff；如果它属于开发侧必须完成的 Verification Obligation，则 `Unproven → BLOCK`。评审者不得把自己无法确认的开发义务默认甩给 QA。

Review 可以执行不会修改源码、Workspace 或外部业务状态的只读检查；执行检查产生的结果只能在确实覆盖对应 claim 时计为证据。

## Finding Gate
只报告会改变“当前实现是否应该进入 QA”结论的问题：

- Requirement 缺失或实现错误；
- Interaction 无法闭环；
- Preserve 被破坏；
- Actual 超出 Expected；
- 工程 owner、dataflow 或 boundary 明显错误；
- runtime correctness 风险；
- 开发侧必要 evidence 缺失；
- Clarification、Workspace、Repo、Diff、Evidence 的真实冲突。

禁止报告命名偏好、格式、无关重构、抽 hook、useMemo、历史技术债或不影响 READY_FOR_TEST 的编码风格意见。

硬规则：

> 如果修复该 finding 不会改变“这份实现是否应该进入 QA”，就不要报告。

## Verdict
只允许两个顶层 Verdict。

### READY_FOR_TEST
必须同时成立：Expected → 已完整兑现；Actual → 没有关键遗漏或未经确认的行为扩散；Preserved → 已确认未被当前改动破坏；Proven → 开发侧必须证明的关键结论有足够 evidence。

输出：

```md
# Verdict

READY_FOR_TEST

## Evidence

- <只列支撑核心交付判断的证据>

## QA Handoff

- <只列明确属于 QA ownership 的剩余检查；无则省略>
```

`READY_FOR_TEST` 只代表达到 QA 接手条件，不代表 `DONE` 或 `delivery-ready`，也不负责排期、测试用例管理或发布。

### BLOCK
任一成立即 BLOCK：

- Clarification 存在且与 Workspace 存在影响行为的冲突；
- 实际交付偏离 `ACCEPTED` 设计决定或 `Binding` handoff，且未获授权改变；
- confirmed requirement 缺失或实现错误；
- 关键 Interaction 无法闭环；
- Preserve 被破坏；
- Actual 引入未经确认的关键行为变化；
- 工程落点明显错误、遗漏或越界；
- 存在足以阻止提测的 runtime correctness 风险；
- 已接受 scope 内必须完成的 Verification Obligation 没有有效 evidence；
- 存在未解决的关键冲突，导致无法形成 Expected；
- Requirement scope 或裁决必需的信息无法确定。

**不自动 BLOCK**：产品现状中发现了未纳入当前 accepted scope 的体验缺口。先记录为产品现状发现，判断它是否属于当前交付目标；只有属于当前 scope 且影响验收时，才进入 blocker。不能把所有产品缺口自动升级为当前 Requirement 的 P0 Blocker。

输出：

```md
# Verdict

BLOCK

## Blockers

| Dimension                                                         | Expected | Actual / Evidence | Impact | Required action |
| ----------------------------------------------------------------- | -------- | ----------------- | ------ | --------------- |
| Requirement / Interaction / Engineering / Preserve / Verification | ...      | ...               | ...    | ...             |
```

每个 blocker 必须写清 Concrete Expected、Concrete Actual / Evidence、为什么阻塞 QA、Required correction。发现 BLOCK 后停止，不自行修复。

## Independence and Mutation Policy
优先在 fresh context / 新窗口执行，不读取实现者的长对话、推理历史、尝试过程、方案辩护或自我评价。除非 canonical artifact 无法恢复且裁决确实依赖其中的事实，否则只读：

- Clarification（如有）
- Design（已接受决定 / handoff）
- PRD / 设计稿（如无 Clarification）
- Workspace（如有）
- Current Repo
- Current Git Diff
- Verification Evidence

禁止：

- 修改代码、测试、Workspace 或任何项目 artifact；
- 自动修复 blocker；
- 代替用户提交、回写单据或发布；
- 发现问题后自己验证修复并宣布 READY_FOR_TEST；
- 创建持久化 Review 报告或第二份 requirement truth。

正确闭环是：Test Readiness Review → BLOCK + evidence + required action → STOP → Original implementation context → fix → Fresh Review Context → review again。

## Stop Rules and Non-goals
以下情况直接 BLOCK，并说明缺失的决策或证据：

- 当前有效输入仍有会改变实现的关键 Unknown；
- Clarification 存在且与 Workspace 产品语义冲突；
- Requirement scope 无法唯一确定；
- 缺少裁决必需的信息，且无法从当前有效输入恢复；
- Workspace 与 Current Repo 严重失配，需要重新 Reconcile；
- 关键判断依赖产品、API owner 或人类决策；
- 缺少已接受 scope 内必须提供且 Reviewer 无法恢复的 runtime / visual evidence。

本 Skill 不承担重新澄清需求、重新设计方案、通用代码质量审计、架构优化、全面性能或安全审计、完整视觉 QA、QA testcase 管理、缺陷跟踪、发布、灰度、回滚、生产监控或发布后分析。
