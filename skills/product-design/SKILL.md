---
name: product-design
description: 用于需求澄清（PRD / 设计稿）、产品语义判断、体验重设计（Journey / IA / 交互 / 呈现）、局部 UI/UX 改善，以及设计解释、体验调整或设计与实现联合探索。纯按已确定设计稿交付代码默认由 Coding Agent 承担。不用于现状逆向、工程实施方案或独立提测审查。
---

# Product Design

## Runtime Contract
- **Outcome**：形成当前任务所需的产品语义、目标体验与设计决定，并标明每项内容的权威状态。
- **Done**：已接受的目标 / 决定足够清楚；任务要求的局部实现与验证已完成，或明确停在设计结论。
- **Next consumer**：Implementation Strategy、Coding Agent、Test Readiness Review。
- **Stop**：不写工程实施方案、不替用户接受产品决定、不把提案写成已确认事实。

## 一个连续的设计空间
需求理解、产品语义澄清、目标行为与体验设计不是必须依次执行的阶段。同一任务可以同时：
- 理解 PRD / 设计稿 / 用户输入在说什么；
- 质疑现有产品规则、对象、状态与生命周期是否成立；
- 形成目标 Journey / IA / 交互 / 呈现；
- 在任务要求时完成局部实现与验证。

不要求入口先选择「澄清模式」或「设计模式」。一个简单 PRD 歧义可以只澄清；一次大型重设计可以同时重构产品模型与体验；一个局部改善可以只动一个 surface。**工作复杂度决定调用多少能力，不由 Skill 名称决定。**

与 Coding Agent 的分界：按已确定设计稿实现、主要目标是交付代码时，默认进入 Coding Agent；只有任务需要设计解释、体验调整，或设计与实现必须联合探索时，本 Skill 才主导并可能完成局部实现。实现中的架构判断、代码设计和技术取舍仍由 Coding Agent / 实施上下文承担。

没有 PRD / 设计稿时，直接从 Current Reality、用户目标与真实约束开始；只有 Product Intent / module purpose 本身 Unknown 时才需要回指，不因缺少 source 而拒绝任务。

## 权威
当前有效的产品输入（PRD、设计稿、用户明确决定）是**意图权威**；Current Reality 是**证据**，不是目标。模型可以提出目标与设计判断，但不因此拥有替用户确认产品决定的权威。

Current Reality 可来自 `.engineering/product/`、`modules/<id>/`、直接阅读 Repo / Runtime 或用户提供的材料；按需消费，不要求先有完整 Baseline。引用 `E-*` / 路径，不重抄长文。

已有的 `clarification/` 与当前有效的 `design/` 决定（`ACCEPTED` 或仍待决的 `PROPOSED`；`SUPERSEDED` 只作历史）同样是当前有效输入；按需消费，不重复推导；其中的 `PROPOSED` 仍不是已接受要求。

每条可能影响工程的决定记录：

```text
D-* / Statement
Status: PROPOSED | ACCEPTED | SUPERSEDED
Basis: DECISION | EVIDENCE | DERIVATION | DESIGN_JUDGMENT
Authority / Accepted-At / Scope / Basis-Ref / Derived-From / Supersedes / Superseded-By
```

- 用户/授权人明确拍板：`ACCEPTED` + `Basis: DECISION`；不需要再经过其他 Skill 批准。
- 模型自己的方案默认 `PROPOSED`；`Basis: DERIVATION` 只说明推导来源，不是 Status，也不自动赋予产品权威。
- 只有 `ACCEPTED`、其严格必要推导，以及由接受决定直接定义的 Preserve / Verification Obligation 进入 Binding。
- `SUPERSEDED` 保留历史指针；不删除，不自动传播。
- 详细规则见 `references/delivery-and-handoff.md`。

## 判断自由
- **Current structure 是 evidence，不是默认约束**：IA / 页面 / 模块边界 / interaction / presentation / morphology 可以保留、重组或替换；「现状如此」不是理由。
- **诊断可以跨出实现范围**：真正的根因或最佳结构在更大范围时，完整诊断、完整设计；本轮是否实现由任务 scope 与真实约束决定。
- **Fact / Diagnosis / Proposal 分离**：只有 FACT 受证据约束；Diagnosis 是推理，Proposal 是设计判断。
- **只为真实取舍发散**：没有结构性分叉就直接收敛给单一推荐；禁止为流程完整造替代方案。
- **成本不是约束**：「改动量大 / 有回归风险」进入取舍与实施顺序，不进入「是否允许改」。
- 只诊断 / 只设计也是合法完成。

## 设计链
```text
User Goal / Job → User Operating Model → Decision / Information Needs
→ Target Journey → Experience Architecture → IA / Workspace
→ Interaction Model → Presentation Model → Component / Control Morphology
```

这是推导方向，不是必须逐步执行的步骤；模型按实际问题自由往返。

## 需求理解与质询
读 PRD / 设计稿 / 素材时，先建立产品目标、模块、主流程与关键规则，再判断哪些地方会让产品理解、研发实现或用户体验明显分叉。

可用的观察视角（不是每次必做的固定程序）：
- **产品语义**：动作改变了什么？生命周期闭合吗？失败 / 取消 / 重复执行留下什么？
- **实现后果**：分开写明的规则组合后能否同时成立？
- **用户体验**：单点是否困惑、丢失、失控？整条路径是否走得通、有出口、前置条件是否在决定前暴露？
- **来源冲突不静默选边**：一致就合并；会造成实质分叉或损失的差异保留为待决，不因模型偏好某一来源而定案。
- **事实与推断分开**：资料明确表达的直接写；基于上下文推断时说明依据；无法可靠判断就停止推断。

这些视角是领域知识，按任务取用；简单澄清不需要三个视角全走一遍。详细问题模式见 `references/clarification/interrogation.md` 与 `references/clarification/clarification-patterns.md`。

## 输出
按任务需要产出，不设 universal mandatory output：
- **澄清文档**：需求范围、主流程、状态与异常、关键风险与待决；写入 `.engineering/requirements/<req>/clarification/`。适用需要产品/设计/研发/测试共同对齐的任务。已有澄清文档随来源更新时，按 `references/clarification/change-aware-update.md` 增量更新，不默认重新生成全部文档。
- **设计决定集**：Target Experience / Journey / 架构 / interaction / presentation 决策，每条带依据、取舍与证伪方式。纯 target 态设计到此即止。
- **实现与验证**（任务要求时）：改动后确认核心任务可完成、关键状态反馈成立、目标 viewport 可用、accessibility 未恶化；声明实际达到的层级 `PASS — CODE / DOM / INTERACTION / VISUAL / NOT VERIFIED`；证据落 `modules/<id>/verification/`。
- **Handoff**（仅存在真实下游消费者、且需要版本追溯时）：`design/module-handoffs/<module-id>/<handoff-id>.md`；内容不可变，Binding 与 Adjustable 分开。简单 UI 修改或同一上下文连续完成的设计+实现不需要快照。

简单任务直接内联，不强制制造文件；不为模板完整度生成 roadmap / alternatives / validation plan。

## 工作区
```text
.engineering/
├── requirements/<req>/
│   ├── sources/          # PRD、设计稿、附件
│   └── clarification/    # 需求 × 交互澄清
├── design/               # 目标体验、设计决定、module handoff
└── modules/<module-id>/  # surface 设计、实现记录、验证证据
```

- 写入 `requirements/<req>/` 时，需求必须显式指定或唯一可推导；多个候选时列出并请用户选择。纯 `design/` 或 `modules/` 任务不需要 requirement slug。
- 用户已给出源料时直接阅读；需要拉取 PRD / Figma 时按 `references/clarification/acquisition.md` 落到 `sources/`，不为走流程重复采集。
- 产品 / 系统 reach 落 `design/`；surface reach 落 `modules/<id>/`；对应模板在 `assets/`。
- 系统级变更在同一 Skill 内更新 `design/` canonical 后继续，不 fork。
- 判断工作区归属、写入位置或准备写入时，以 `references/workspace-and-ownership.md` 为唯一权威。

## Reference routing
|当前问题|读|
|---|---|
|PRD / 设计稿来源不清、互相冲突，需要判断以什么为准|[references/clarification/source-reading.md](references/clarification/source-reading.md)|
|需要拉取 PRD / Figma 源料|[references/clarification/acquisition.md](references/clarification/acquisition.md)|
|要写澄清文档：目录、模块拆分与写法|[references/clarification/output-shape.md](references/clarification/output-shape.md)|
|需要判断哪些澄清问题值得问、避免低价值提问|[references/clarification/clarification-patterns.md](references/clarification/clarification-patterns.md)|
|质询 PRD / 设计稿时不确定从哪些维度提问|[references/clarification/interrogation.md](references/clarification/interrogation.md)|
|已有澄清文档需要随来源更新|[references/clarification/change-aware-update.md](references/clarification/change-aware-update.md)|
|PRD / Figma 采集失败或环境阻断|[references/clarification/environment-boundary.md](references/clarification/environment-boundary.md)|
|需要判断设计问题的根因、ownership、约束与验证层级|[references/design/design-framework.md](references/design/design-framework.md)|
|需要形成界面构图或 presentation 模型|[references/design/presentation-synthesis.md](references/design/presentation-synthesis.md)|
|需要判断工作区归属、写入位置或准备写入|[references/workspace-and-ownership.md](references/workspace-and-ownership.md)|
|事实被修正、旧结论失效|[references/evidence-and-correction.md](references/evidence-and-correction.md)|
|涉及决定状态、Binding 或 handoff|[references/delivery-and-handoff.md](references/delivery-and-handoff.md)|

## 禁止
- 禁止把 `PROPOSED` 写成 `ACCEPTED`，或用「推导合理」代替用户接受。
- 禁止在澄清任务里顺手交付未要求的目标设计，或在设计任务里把现状当成必须保留的约束。
- 禁止只看到源码就宣称视觉 / 交互已验证。
- 禁止把 Target 设计写成 Current 事实，或占用 Current Reality 的 `J-*` 身份。
- 禁止顺手重写无关模块；授权范围 = 当前任务负责的 surface / reach。
- 禁止在探索阶段生成没有当前消费者的 handoff。
