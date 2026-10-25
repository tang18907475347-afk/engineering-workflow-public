# 深度模式：完整 Baseline 与实现规格（Replica-Ready）
> **进入深度模式时，先完整读完本文件，再按文末的 Reference routing 读取其他文件。** 深度模式适用于系统 / 模块 / 业务域级的现实理解、复刻、迁移、审计、结构性重构，或任何需要 Coverage、Design Readiness、Replica-Ready 判断的任务。
> 本文件内容自 SKILL.md 原文逐字迁移，规则与 v1 完全相同。核心不变量保持原编号：1–4、12、13 在本文件，5–11 在 SKILL.md「核心不变量（两条路径共用）」。

## 调查契约
Product Reality 根据用户目的确定交付，根据目标 Scope 确定完整性边界，根据所需调查严格度确定证据和行为恢复标准。

- **Scope（目标范围）**：用户选定的逆向边界——单链路、模块、业务域或完整系统。不默认全产品；Replica-Ready 可应用于任何 Scope。
- **Rigor（调查严格度）**：证据与行为恢复需要达到的程度。`Design-Ready` 与 `Replica-Ready` 是相应任务的完成判断，不是严格度等级本身。
- **Purpose → Deliverable**：诊断→答案；优化/理解→模型；复刻/重建→实现规格（spec）。交付形态由目的决定，不由 Scope 或 Rigor 决定。

完整 Baseline 的完整性边界是 **Baseline Scope**（本次系统现实调查覆盖的范围）；Replica-Ready 的完整性边界是 **Spec Target Scope**（独立 Coding Agent 需要重建的范围）。调查范围可以大于复刻范围，两者不要求相等；各自只由对应产物签发，不能互相替代或独立裁决。同一 Inventory item 分别记录 `Baseline Relation` 与 `Spec Relation`；调查范围与复刻范围不合并，跨边界依赖不自动进入复刻范围。每个 Scope 的 disposition 独立；一个 Scope 的 `COVERED` 不能替代另一个 Scope 的判断。

Scope 与 Rigor 独立组合；同一 Scope 可用不同 Rigor，同一 Rigor 可应用于不同 Scope。Agent 从任务意图自主判断 purpose / scope / rigor / deliverable，只有实质歧义才询问；预设对用户可见、可调整，不要求用户每次填写，也没有固定 Mode 或流程矩阵。不得因 Skill 被激活而默认执行系统级逆向、完整覆盖或生成固定产物；也不得把最小调查、只覆盖核心路径或零持久化当成默认工作形态。

完成标准不是「Baseline 建好了」或「Coverage 达标了」，而是「当前知识是否足以支持用户要求的下一步」。Coverage、Baseline、Design Readiness 与 Replica-Ready 服务于这个判断，不自行定义完成。

对于 Replica-Ready，必须充分发现 Spec Target Scope 内的行为契约，恢复能够影响重建正确性的业务规则、状态、接口、数据、副作用及异常路径。所有已发现且相关的行为必须有明确处置（COVERED / EXEMPT / OPEN），不允许静默遗漏；OPEN 项必须进入 Unknown Registry 并标明是否 blocking。**Inventory COVERED 不等于行为契约已恢复**：一个 in-scope 能力可以对应多个 `B-*`，必须恢复每个 `B-*` 的条件、状态、分支、副作用与异常路径。EXEMPT 必须基于真实范围边界，不能仅以「不是 User Job」排除 Spec Target Scope 内的系统能力。必要的外部依赖按其对目标行为的影响恢复契约，不自动扩大复刻范围；**依赖契约完整性 ≠ 依赖系统内部完整性**。

最终结果必须可以被未参与调查的 Coding Agent 独立消费。是否达到 Replica-Ready，由实际规格充分性和阻塞缺口决定，不能由文档数量、覆盖百分比或结构校验自动认定。

常见目的对应的默认建议（可调整，不是等级或固定流程）：

|用户目的|逆向重点|合理产出|
|---|---|---|
|定位一个问题|解释故障所必需的机制与因果链|根因、证据、影响范围|
|优化局部体验|相关用户路径、状态、依赖与约束|当前行为模型、体验问题|
|深入理解模块|模块职责、完整状态与行为、上下游系统关系|模块机制与用户路径知识|
|复刻现有产品|目标范围内的系统行为、完整用户旅程、交互状态、异常与边缘路径|足以指导高保真复刻的实现规格|
|重构现有产品|目标范围内的完整当前事实、产品约束、关键与边缘路径、现有问题|可支持结构性重新设计的 Reality Baseline 或实现规格|

「先打通核心链路」只适用于探索价值、确定优先级或目标尚未成立时。用户明确要求深入逆向、复刻或结构性重构时，核心路径是起点，不是完成标准；目标范围内的边缘路径、异常、取消/重试/恢复、权限与前置条件、跨模块状态关系属于行为契约，不能用核心路径已覆盖替代完整性。未观察或未验证的部分必须明确标记，不得用推断填补。

重构场景的完整理解不等于完整保留现状：旧产品的边缘行为可能应删除、合并或重新设计，但必须先理解其作用与影响，才能作出有依据的取舍。

深度与持久化是两个独立维度：

| | 轻量调查 | 深度调查 |
|---|---|---|
| 不持久化 | 回答局部代码问题 | 完成复杂分析后直接交付结论 |
| 持久化 | 保存一个关键事实 | 建立完整产品现实知识 |

- 局部诊断允许有界调查和零持久化；系统理解、产品复刻和结构性重构必须在**选定 Scope 内**恢复足以支持目标的行为契约，不得以核心路径已覆盖替代目标范围内的完整性。
- 用户目的决定所需理解的充分性，不是机械限制调查范围：局部问题的根因涉及跨模块机制时，主动扩大调查，不被「局部任务」标签限制；但调查广度不等于复刻广度，跨边界发现的依赖按依赖契约处理，不自动纳入复刻范围。
- 完整 `product/` 现实适用于系统级逆向、复刻/迁移/审计、结构性重构或需要 Coverage 与 Design Readiness 的任务；它是调查结论，不是默认前置。单链路/模块级 Replica-Ready 可以直接产出实现规格，不强制初始化全套 Baseline 产物。
- 仅在知识具有明确持续消费价值时持久化；产物形态由知识性质及消费者决定。
- 产物必须反映实际证据与理解程度：区分已验证事实、推断与未解决缺口；不得把未覆盖范围描述为完整理解。实现规格可以承载完整开发级语义，但每个重要结论必须可追溯到 canonical `E-*` / `C-*` / `J-*` / `B-*`。
- Evidence 发生变化后，受影响的实现规格必须重新核对并更新；不声称自动重生。
- 轻量代码问题不启动产品逆向；当前问题闭合即停，**零写入是合法结果**。这是局部诊断的形态，不是全局默认。
- 只有真的观察到新事实才记录；不为「完整」补记录。
- 没有 Baseline 不等于证据不足：直接读 Repo / Runtime / 测试 / 数据快照，标注实际范围。
- 需要跨会话继续时，把状态放进 canonical 产物，不依赖会话记忆。

## 产品建模不变量（1–4、12、13）
1. **User Job ≠ 页面/模块**——Route、Tab、Modal、Landing、Settings、History 默认只是 Surface。
2. **User Job ≠ 内部工作流**——检索、路由、队列、后台阶段、API、自动 Loop 默认属于内部实现；只有迫使用户等待、判断、批准、选择或恢复时才进入 Journey。判定动作：它的 failure、omission、latency、gating 或 output form 是否改变用户可观察或可操作的东西？是 → 进入 Coverage 与 Behavior 调查；否 → 记 `EXEMPT`，理由必须是对本问题的否定回答。
3. **User Job ≠ 异常/控制机制**——stop/resume/retry/autosave/conflict/error 默认进入 Behavior Contract。
4. **同层级同粒度**——禁止把端到端结果、一键动作、异常机制并列为同级 Job。
12. **产品现实的 Primitive 只有一套，且都是 `E-*`**——禁止为 Interaction / Presentation 新建 ID namespace；事实类型由 `Kind` 表达。Product Model / Journey / Behavior / Coverage 是 derived view，不得被当作 Product Reality 的全部。Subject 只表示被观察对象的身份（`reference:xxx` / `implementation:xxx` / `self`）。代码机制缓存不使用 `E-*`，也不属于产品现实的 primitive。
13. **「产品本身不完整 / 部分自洽」是合法的高质量结论**——不要求交出完整自洽的 Product Model；禁止把 Unknown 补成设计、把断开的 Journey 补成正常、把历史残留解释成产品意图。

## Runtime Experience Observation（条件触发，不是固定税）
Source 与 Runtime 解决不同问题，不互相替代：
- **必须触发**：任务属 replication / fidelity / clone / reference implementation / 还原已有产品 / 对齐现有可运行系统，或用户已提供 reference runtime、端到端截图、录屏、walkthrough → 每个 P0/P1 Journey 必须含 Runtime Experience Evidence。
- **按需触发**：Source 无法确定 P0 Journey；Interaction Primitive 不明确；用户入口 / 下一步提示 / 可见反馈无法由已有证据确认；Source 与 docs 冲突。
- **不强制**：backend / service only；无 UI 且无 reference runtime；用户只需要 capability / system map。

观察点由 User Job 驱动，不由页面数量驱动；禁止全站截图、穷举状态探索。过程如何变化写 `Kind: interaction`，界面结构长什么样写 `Kind: presentation`；不保存像素、全部 spacing、完整 DOM。

## 收口
- 建立完整 `product/` Baseline 时，Design Readiness 的判据以 `references/product/coverage-and-readiness.md` 为唯一权威；最终完成标准仍是「当前知识是否足以支持用户要求的下一步」。`Baseline Status = COMPLETE` 只表示调查已诚实收口，不表示产品完整。
- Replica-Ready 是相对于 **Spec Target Scope** 的完成判断：由实现规格充分性与阻塞缺口决定，不由文档数量、覆盖百分比或结构校验自动认定。判据、依赖契约边界与 EXEMPT 语义见 `references/product/coverage-and-readiness.md`。
- Replica-Ready Judgment 的单一来源是 `spec/INDEX.md`；`BASELINE_INDEX.md` 只引用（若有 spec），不重复签发。Baseline Scope 与 Spec Target Scope 分别由 `BASELINE_INDEX.md` 与 `spec/INDEX.md` 签发；调查范围可以大于复刻范围。
- 实现规格（`spec/`）是 derived view，可承载开发级语义，但每个重要结论必须可追溯到 `E-*` / `C-*` / `J-*` / `B-*`；Evidence 变化后必须重新核对并更新受影响节，不声称自动重生。
- 仅在建立完整 Baseline 或产出实现规格时运行 `python scripts/check_baseline.py <product-root>`；它只做确定性结构与引用校验，不证明语义收口、行为覆盖或规格充分性。

## Reference routing
|当前问题|读|
|---|---|
|决定持久化完整 product/ 或实现规格时，新建或维护目录、分片与 Index|[references/product/artifact-layout.md](references/product/artifact-layout.md)|
|决定建立完整 product/ 或做大型逆向时，确定 Inventory、搜索与 Trace 范围|[references/product/reconnaissance-protocol.md](references/product/reconnaissance-protocol.md)|
|写入 product/ 证据时，使用 E-* / C-* 字段并判断 facet、Channel 与 Boundary|[references/product/evidence-standard.md](references/product/evidence-standard.md)|
|建立持久 product/ 模型或实现规格时，从证据形成 Product Model / Job / Journey / Behavior / spec view|[references/product/modeling-rules.md](references/product/modeling-rules.md)|
|建立完整 Baseline 或判断 Replica-Ready 时，确定 Coverage、Design Readiness 与 scope-relative 完成标准|[references/product/coverage-and-readiness.md](references/product/coverage-and-readiness.md)|
