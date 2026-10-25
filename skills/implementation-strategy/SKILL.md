---
name: implementation-strategy
description: 用户要求工程实施方案、开发落点、ownership 判断、Scope / Refactor / Migration / Completion 评估、执行期 Workspace Reconciliation 或交接开发时使用。产品语义冲突与关键缺口由 product-design 处理；有缺陷单据上下文的缺陷任务由 bugfix 处理。
---

# Implementation Strategy

## Runtime Contract
- **Outcome**：把有效 Product Intent 与 Current Repo 转成可评审、可执行的 Guidance；复杂任务可持久化为 Workspace。
- **Next consumer**：Human 评审者与基础 Coding Agent。
- **Stop**：完成工程判断或 Workspace 修订后停止；不执行代码修改，不替用户裁定未决产品语义。

## 工程判断与边界
本技能判断真正要改变什么、行为由谁拥有、现有实现为什么不满足目标，以及什么证据足以证明正确。功能、重构、迁移、Scope 评审与完成评审使用同一领域能力，不设专用 Mode 或固定推理顺序。

Product Intent 可来自 PRD、设计资料、ticket、当前对话、明确 Human Decision 或已接受的设计决定 / Binding handoff；不强制先补上游产物。Current Repo 证明现状、ownership 与能力约束，不能用现状覆盖新的产品要求。已接受输入优先复用；有疑点、缺口或冲突时可以按需回源核查，不因上游未显式标 UNKNOWN 就停止调查。核查不授权重新决定产品行为；确实未决且影响实施的语义才交给用户或对应 owner。见 [references/product-inputs.md](references/product-inputs.md)。

方案首先完整满足当前需求、关键 Preserve 与正确性，再比较非必要的变更面、抽象和维护成本。必要的跨模块改动不是 scope expansion；无关统一、历史清理或未来能力不因规划任务自动获得授权。现有模型足够时保持局部；错误 ownership、状态模型或协议导致 failure 时，允许修到根因闭合，不以行数最少为目标。

调查范围取决于真实可达路径与行为契约，不是已发现调用方的集合。当前调用方未使用、UI 未暴露、关键词未命中，都不能证明某能力不存在或不可达。声称“全部受影响入口 / 不存在其他路径”时需有支持该边界的调查证据；否则说明当前已发现集合与未知。权限、可见性与访问限制尤其要考虑绕过当前入口后的独立访问路径。相关工程陷阱见 [references/plan-quality.md](references/plan-quality.md)。

结论强度不能超过证据。工程推断可以由模型判断；改变产品行为、协议或验收口径的未知不能写成事实。新增取值或修改共享能力时，按真实消费者检查 fallback、穷举、排序、协议副本与用户可见出口，不要求固定矩阵。

**按需复用已有知识**：
- 高恢复成本、跨文件且值得复用的代码机制，可先查 `.engineering/intelligence/` 相关分片；简单查找直接读源码。命中是线索，关键事实仍以 Current Repo 核验；stale hit 按缓存契约修正或删除。需求取舍、产品决定和验证计划留在 Workspace。
- `.engineering/product/`、`design/`、`clarification/` 相关且可信时引用稳定 ID 或路径，不重抄长文。没有 Baseline 不等于证据不足，可以直接观察 Repo / Runtime。
- 消费 handoff 时区分 Binding 与 Adjustable，记录实际消费的 handoff-id；PROPOSED 不自动成为要求。
- `requirements/<req>/reality.md`（需求级现状摘要）存在时，用它的主链路、行为契约与候选 Preserve（`PC-n`）作为工程落点与 Preserve 的起点，你依赖的事实仍按 Current Repo 核验；不存在时直接调查 Repo。
- `.engineering/context.md`（业务上下文）存在时先读：业务规则与术语会影响方案与验证口径。

## 可执行交付
Guidance 的结构随任务与实际读者选择，可以是直接答复，也可以是计划、落点说明或独立任务；不把 PRD 章节机械转换为 Task。

执行者需要理解目标行为、当前机制、真正 owner、必要修改、关键不变项，以及如何验证。已确定且影响编码或验收的事实应转为工程输入，例如实际配置 / seed、固定文案、状态转换、调用语义或事件参数；仅给 schema 或“按 PRD 实现”不能替代这些信息。保留来源指针用于核查，不要求执行者重新作已完成的产品决策，也不禁止其在发现缺口或漂移时回源。

验证应证明目标行为和关键 Preserve，而不是只证明命令成功。根据实际风险选择 unit、integration、browser、runtime、截图或 contract 等证据，并说明必要的账号、数据、环境或 mock 从何获得。代理断言不能冒充未观察到的真实行为；缺口如实保留，不按测试类型自动转人工。

持久化 Workspace 时，`plan.md` 有两节固定接口：开头的「给执行者」，以及「验收与保持」（`AC-n` / `P-n`，每个任务注明覆盖哪些）。前者让不加载本 Skill 的执行者也知道在哪里停、怎么记录；后者让执行者、TRR 与 bugfix 用同一份期望，而不是各自重新推导。格式见 [references/workspace-format.md](references/workspace-format.md)；交付前运行 `scripts/check_plan.py` 检查覆盖关系。其余章节仍按任务自由组织。

Phase / Task 只在真实依赖、交付、ownership 或验证边界值得拆分时出现。产品或协议决定、外部依赖、高返工选择确需人裁决时，说明待决问题、影响和当前能否继续；不强制分类或建立 Gate。高影响风险需要可执行的处置与验证，不要求绑定一个不存在的 Phase。

## Workspace 与恢复
需要持久化时，一个 Requirement 保持一个 canonical Workspace，位于项目 `.engineering/requirements/<requirement-slug>/workspace/`。Requirement scope 按显式指定、唯一可推导、歧义时询问确定；项目根与写入边界见 [references/workspace-and-ownership.md](references/workspace-and-ownership.md)。`sources/` 与 `clarification/` 是只读上游输入，不维护双向同步。

`plan.md` 是当前实施入口；章节自由，导航入口可内联，只有单独维护更方便时才建 `anchors.md`。Phase 文件、一次性人读 `brief.md` 均按需，不创建空章节或占位文件。格式及 brief 生命周期见 [references/workspace-format.md](references/workspace-format.md)。Workspace 默认本地忽略；用户要求提交时遵循项目约定。

Workspace 记录当前可执行真相，不是 changelog。当 Repo、有效 Human Decision、依赖或验证结果使现有指导会导致错误实现 / 完成判断时，原地修订受影响内容：保留仍有效事实，替换或删除 stale 方案、任务与证据，重新判断受影响任务。执行 Agent 可以完成这些局部修订与必要回源；重大新需求仍由用户明确范围，不反向篡改 Product Intent。留下足以恢复当前位置、未决项与维护方式的简短说明，不新增状态机。历史只在已纳入版本控制时由 Git 保留。

## 完成判断
声明提测条件就绪前，对照 Workspace、Current Repo / worktree 与有效验证证据，处理已知 blocker、未决高影响决定及 stale 完成声称。既有失败需与本次回归区分；必要外部前置未就绪时不能假装验证完成。

提测条件就绪不等于测试侧验证已完成；DONE 表示当前需求实现与约定验证义务完成；delivery-ready 还需处理交付前必须退出的 mock、debug entry、临时 flag / 数据 / 协作代码等 Delivery Liabilities，确认替换或删除后构建与必要验证仍成立。只记录真实负债的位置、依赖与退出条件，不建固定 Schema。

这是实施侧自检，不替代用户要求的独立 `test-readiness-review`，也不承接部署、灰度、生产监控、QA 排期或缺陷管理。交付前消除会误导执行者的矛盾、缺失工程输入和重复内容；不以“假设删除全部来源”要求复制整套上游资料。

## Reference routing
|当前问题|读|
|---|---|
|看不懂某个术语（Status、Basis、Binding、五个面、Scope / Rigor、AC / P 等）|[references/glossary.md](references/glossary.md)|
|写 Workspace、拆分 Phase / Task 或一次性 brief|[references/workspace-format.md](references/workspace-format.md)|
|判断共享模型、调查边界、风险与验证|[references/plan-quality.md](references/plan-quality.md)|
|消费 PRD / 设计稿 / 已接受决定 / handoff|[references/product-inputs.md](references/product-inputs.md)|
|判断工作区归属与写入边界|[references/workspace-and-ownership.md](references/workspace-and-ownership.md)|
|修正失效事实|[references/evidence-and-correction.md](references/evidence-and-correction.md)|
|决定状态、Binding 或 handoff|[references/delivery-and-handoff.md](references/delivery-and-handoff.md)|
