---
name: product-engineering
description: 当用户需要在产品现实、产品设计、工程实施、提测审查、AI 评审问题或缺陷之间选择下一步，继续已有需求，或无法唯一命中某个业务 Skill 时使用。只路由到唯一主能力或基础 Coding Agent，不执行下游任务、不自动串行推进。
---

# Product Engineering

## Runtime Contract
- **Outcome**：根据用户真实意图选择正确的业务能力，并说明当前输入、产出与下一消费者。
- **Done**：主 Skill 已确定，或已明确直接实现；scope 已明确，调用方知道做到哪里停止。
- **Next consumer**：被选中的 Skill、执行者或 QA。
- **Stop**：只选择、交接、停止；不执行下游任务、不维护跨 Skill 状态、不自动串行推进全流程。

`Coding Agent` 指宿主 Agent 在不加载业务 Skill 时的实现角色，不是独立 Agent、subagent 或可调用工具；Router 中对应“直接实现”。

## Capability Map
这些能力不是必须按序执行的流水线，也不预设「先逆向、再设计、再实施」。按用户目标选择；用户已提供充分、可信的现状时可直接进入设计或实施，简单任务可以直接实现。

```text
理解现在：product-reality（按需）
定义目标：product-design（按需）
工程实施：implementation-strategy → 直接实现 → test-readiness-review → QA
独立通道：ai-code-review（合并前 AI 评审问题）
独立通道：bugfix（缺陷）
```

|能力|什么时候用|主要输入|核心产出|Stop|
|---|---|---|---|---|
|`product-reality`|需要理解现有系统：代码机制、跨文件链路、产品行为、用户路径、证据边界|Repo / Runtime / Docs / 用户问题|直接回答，或 `.engineering/intelligence/` / `.engineering/product/` 的当前事实|不做目标设计或实现；不预设调查深度，不把轻量问题升级成完整 Baseline|
|`product-design`|任务需要决定或调整目标产品体验，可能伴随设计侧局部实现|PRD / 设计稿 / 用户输入 + 按需消费 Current Reality|`clarification/`、`design/`、`modules/<id>/` 的决定与实现|不把提案冒充已接受要求；不写工程方案|
|`implementation-strategy`|目标已足够明确，需要映射到工程现实|目标 / 澄清 / 设计 + Current Repo|`.engineering/requirements/<req>/workspace/` 的可执行计划|不直接编码|
|直接实现|任务主要目标是交付代码，即使实施包含架构判断、代码设计或复杂技术取舍|计划 + Repo，或直接任务输入|实际实现 + 验证证据|不自行承担独立 READY_FOR_TEST 裁决|
|`test-readiness-review`|Requirement 主要实现完成，准备判断能否提测|Expected + 实际交付 + 证据|`READY_FOR_TEST` / `BLOCK`|不修代码、不重新规划、不代替 QA|
|`ai-code-review`|处理 MR 上云端 Agent 生成的 AI 评审意见：逐条验证、修复、关闭 / 延期 / 补证并反馈|MR + Repo + Diff + 证据|本地判断 + 修复 / 验证 + 平台反馈|不自己发起评审；不代替提测裁决；不自动合并|
|`bugfix`|用户执行缺陷单据的采集、分析、修复或回写|缺陷单据 + Repo + 证据|snapshot / dossier / fix / triage|停在用户点名的 channel|

> 代码机制调查已并入 `product-reality`；`intelligence/` 的产物路径与缓存契约保持不变。

## Intent Routing
按用户动作和当前目标路由，不按 URL、单据类型或输入来源机械路由：

|用户目标 / 典型表达|路由|判断边界|
|---|---|---|
|“这个产品现在到底怎么工作”“重建现状/交互/用户路径”“这个参考系统怎么实现”“这个业务链路怎么走”“状态谁写的”|`product-reality`|关注 Current Reality 与证据；调查深度由用户目标与知识缺口决定，不强制 Baseline|
|“为复刻/重构恢复当前产品现实”“把现有行为、状态、异常路径摸清”|`product-reality`|目标是先理解现状；Scope（单链路/模块/域/系统）由用户选定，不默认全产品；复刻/重构要求目标范围内的边缘路径，不以核心路径替代完整性|
|“目标体验怎么设计”“这个页面/流程应该怎么改”“设计稿需要解释或体验调整”“帮我看看这个需求”“PRD 和设计稿有没有冲突”|`product-design`|任务需要决定或调整目标产品体验；纯按已确定设计稿交付代码默认直接实现|
|“这个需求怎么实现”“改哪些地方”“给我实施方案”|`implementation-strategy`|目标已足够明确；仍有会改变方案的未知时先澄清或设计|
|“按计划实现”“按已确定设计稿交付代码”“开始写代码”“把这个简单改动做掉”|直接实现|任务主要目标是交付代码；即使包含复杂技术判断也直接实现，不以机械实现为分界。有 Workspace 时，先读 `plan.md` 开头的「给执行者」与「验收与保持」|
|“代码写完了，帮我提测前检查”“看看能不能提测”|`test-readiness-review`|审查 Requirement 的 Expected × Actual × Preserved × Proven；不路由成传统 code review|
|“处理 AI 评审意见”“这条 MR 评论说得对吗”“误报就关掉”“修完回复并复审”|`ai-code-review`|外部 finding 是待验证发现；没有 PRD / Workspace 也能独立处理|
|“收集我的 bug”“分析这个缺陷单”“修这个缺陷”“回写 fixed”|`bugfix`|按用户点名的 action 选 channel；单据 URL 只提供上下文|

需求单若被用户作为产品输入理解或实施，按真实目标进入 `product-design` 或 `implementation-strategy`，不因来源是缺陷平台自动进入 `bugfix`。

## 知识消费
- 先读 `.engineering/context.md`（业务上下文，如有）：业务目标、术语与过去被纠正过的理解，会影响路由判断（例如“这是设计问题还是实现问题”）。没有这个文件不影响路由。
- 若 `.engineering/` 已存在与当前任务相关的 Current Reality、目标设计、澄清或计划，按需消费，引用 `E-*` / `C-*` / `J-*` / `B-*` / `D-*` / handoff-id 或路径，不重抄长文。
- 没有相关上游知识时，直接从 PRD、设计稿、Runtime、源码开始；不要为了“流程完整”先跑 Baseline、Clarification 或 Handoff。
- `product-reality` 的 `intelligence/` 是代码机制缓存，`product/` 是产品证据；两者可以引用同一段源码，不要求统一 schema，也不要求只保留一份。
- MR 上的 AI 评审意见是外部发现，不是已确认事实；先按当前代码、Diff、测试与运行证据验证。没有 PRD、Workspace、Clarification 不构成阻塞。
- 上下游知识冲突时，记录冲突并按 `references/evidence-and-correction.md` 修正失效事实；涉及决定状态或 handoff 时按 `references/delivery-and-handoff.md` 判断；不静默覆盖，也不把旧知识当作免于核验的权威。
- 允许在计划或设计中保留局部摘要，但不得维护另一份与 canonical 冲突的权威。

## Handoff / Stop
各能力只交接已有 canonical artifact 或明确的执行结果，不新增统一 state、current-stage 文件、current requirement pointer 或中间 artifact：

```text
product-reality → Current Reality（直接回答 / intelligence / reality.md / product）
product-design → 产品语义 + 设计决定 +（按需）局部实现 / 验证 +（按需）module handoff
implementation-strategy → executable Requirement Workspace
执行者 → implementation + verification evidence
test-readiness-review → READY_FOR_TEST / BLOCK（+ reviews/ 下的审查记录）
ai-code-review → 本地 verdict + 修复 / 验证证据 + 平台反馈状态
bugfix → issue dossier / fix / triage result
```

- `product-reality` 不写 Future-State；`product-design` 不把 `PROPOSED` 当成 `ACCEPTED`。
- `product-design` 不写工程实施方案；`implementation-strategy` 不直接编码。
- 执行者完成实现与自身 verification 后停止；独立裁决由 fresh Review Context 中的 `test-readiness-review` 完成。`BLOCK` 后由原实现上下文修复，再重新 Review；Router 不自动循环。
- `test-readiness-review` 不修改代码、Workspace，不重新规划，不代替 QA。
- `ai-code-review` 对范围内 finding 给出本地判断；`adopt/ignore/reject` 只是外部反馈，不等于代码已修或问题已关闭；不自动合并 / 推送。
- `bugfix` 严格停在用户请求的 channel；QA 发现 defect 后，只有用户明确要求操作缺陷单据才进入它。
- Router 只在用户明确要求或当前目标确实依赖多个能力时组合；完成当前交接后停止，不偷偷推进下一阶段。
- 路由到 product-reality 时，说明本次调查的目的、Scope、Rigor 与交付假设；默认建议可调整，Scope 显著扩大、Rigor 升级为 Replica-Ready 或目标不明确时让用户参与决策。

“继续推进这个需求”“现在到哪了”这类请求，先运行只读的进度脚本，再结合用户意图判断下一步：

```bash
python3 <本 Skill 所在目录>/scripts/req_status.py [<requirement-slug>]
```

它只从现有产物读出事实（澄清、`reality.md`、计划与任务完成数、最近一次审查结论），不写任何状态；输出里的“参考下一步”只是提示，与用户意图冲突时以用户意图为准。脚本不可用时，按下文的最小读取规则自己判断。

Scope 解析遵循：`explicit > uniquely inferable > ambiguous → report / ask`。只有歧义会导致不同 Skill、不同 Requirement/单据 scope 或不同最终行为时才停止；能唯一推断则直接路由。

定位 scope 或判断写入边界时，读 [references/workspace-and-ownership.md](references/workspace-and-ownership.md)。Router 只读定位显式或唯一可推导的 scope，不预先遍历全部资产，也不修改 `.gitignore` 或其他项目文件。

## Reference routing
|当前问题|读|
|---|---|
|看不懂某个术语（Status、Basis、Binding、五个面、Scope / Rigor、AC / P 等）|[references/glossary.md](references/glossary.md)|
|定位 scope 或判断写入边界|[references/workspace-and-ownership.md](references/workspace-and-ownership.md)|
|上下游知识冲突、需要修正失效事实|[references/evidence-and-correction.md](references/evidence-and-correction.md)|
|涉及决定状态或 handoff|[references/delivery-and-handoff.md](references/delivery-and-handoff.md)|
