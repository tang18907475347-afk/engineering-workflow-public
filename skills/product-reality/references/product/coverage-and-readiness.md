# Coverage 与 Design Readiness
本文件是 Coverage 规则、Design Readiness 与 Replica-Ready 判据的唯一权威。`scripts/check_baseline.py` 只做其中可机械判定的记录契约与引用完整性，不判断语义真伪。

**适用范围**：本文件约束「选择建立完整 `product/` Baseline 或实现规格（Replica-Ready）」时的 Coverage 与收口标准；所有规则相对于用户选定的 Target Scope 成立，不默认全产品。它不是调查入口，也不定义调查默认深度；轻量调查、局部代码问题或一次性结论不要求满足本文件。

**完成标准来自下游用途**：Coverage、Baseline、Design Readiness 与 Replica-Ready 只服务于一个判断——当前恢复的知识是否足以支持用户要求的下一步。它们不自行定义任务完成；目标不同、Scope 不同，充分性标准不同。

**Scope 术语**：`Baseline Scope` = 本次系统现实调查覆盖的范围，由 `BASELINE_INDEX.md` 签发；`Spec Target Scope` = 独立 Coding Agent 需要重建的范围，由 `spec/INDEX.md` 签发。调查范围可以大于复刻范围；两者不要求相等，也不能互相替代或独立裁决。本文的 `Target Scope` 指当前交付的完整性边界：完整 Baseline 用 `Baseline Scope`，Replica-Ready 用 `Spec Target Scope`。

**Status 值（BASELINE_INDEX.md frontmatter）**：`IN_PROGRESS` = 调查进行中；`PARTIAL` = 已有可靠结论但存在使其不完整的缺口；`BLOCKED` = 明确知道需要什么证据或条件但当前不可获得；`COMPLETE` = 理解已诚实收口（≠ 被调查产品完整，见 §7）。

Structural Validation（`PASS / FAIL`）与 Status 是两个独立概念：Structural Validation = PASS **不代表**可以收口，也不代表语义判断已成立。

## 1. Inventory Coverage（分母外部化）
需要建立 Coverage 文档时，可参考 `assets/coverage.template.md`；只使用当前 Scope 适用的表，不为无 UI 的任务补体验表。
分母来自 reconnaissance 的 Inventory（Surface / Route / API / Runtime Executor / Authoritative Docs / Persistence / Background Job / admin-config-legacy 等类型），**不由 Question Ledger 自己生成**。理由：若分母由模型已想到的问题定义，模型没发现的对象就永远不会出现在 Coverage 里，收口检查也看不见这个遗漏。

每个 Inventory item 必须有两个关系字段（见 `reconnaissance-protocol.md` §1）：`Baseline Relation`（相对于 `Baseline Scope`）与 `Spec Relation`（相对于 `Spec Target Scope`；无 spec 时 `—`）。每个 scope 有独立 disposition：

- `Baseline Disposition`：对 Baseline Relation 的 `in-scope` / `dependency` 项；`COVERED / EXEMPT / OPEN`。
- `Spec Disposition`：对 Spec Relation 的 `in-scope` / `dependency` 项；`COVERED / EXEMPT / OPEN`；无 spec 时 `—`。
- 两边 `out-of-scope` 都只记录边界。

共享定义：

- `COVERED`：链接 ≥1 条 Question 或 Evidence；Surface 类同时给出 Classification（`USER_TASK / SUPPORTING / CROSS_CUTTING / ADMIN_CONFIG / LEGACY_DEAD / UNRESOLVED`）并关联相关 Job（如适用）。若该 item 有行为契约，还必须列出相关 `B-*`，并确认每个 `B-*` 已处置。
- `EXEMPT`：理由必须相对于当前调查的 Target Scope，并有证据。全产品理解用不变量 2 判断是否产品面；scoped Replica-Ready 用「不在 Spec Target Scope」或「依赖内部与目标行为无关」判断（见 §8.1）。不得以「不是 User Job」「属内部实现」「非产品面」「不重要」「太复杂」「暂时跳过」排除目标范围内的系统能力；系统能力即使不是独立 Job，只要在 Target Scope 内就必须处置。
- `OPEN`：尚未处置。收口前必须清零，或逐项转入 Unknown Registry 并判定为不影响 P0/P1 与关键 Behavior（接不变量 8）。不得用 OPEN 承载「难查所以先放着」。

**Inventory COVERED 不等于行为契约已恢复。** Inventory 只回答「发现了哪些能力、入口、对象及依赖」；一个 Inventory item 可以对应多个 `B-*`，每个 `B-*` 的条件、状态、分支、副作用与异常路径必须分别恢复或有显式 Unknown。完整性分母仍是 Inventory，但完成判断必须深入到 `B-*`；不新增 Feature Registry。

**类型级完整性**：Inventory 每个类型至少 1 项，或在 `coverage/*.md` 的 Type Completeness 表写明「本项目确实不存在」还是「未找到 + 实际检索方式」。运行期执行器与权威文档两类为空是高风险信号，必须写清属于哪种情况。

这不要求把每个文件 / API / 内部函数都塞进 Inventory：分母仍是 reconnaissance 识别出的主要产品区域、运行期执行器与权威文档。

## 2. Object Lifecycle（核心对象理解）
每个 Core Object 至少检查适用阶段：`create/import / inspect-use / modify / validate-approve / publish-share-export / archive-delete / history-recover`。

每格只能是：`VERIFIED / UNSUPPORTED_WITHIN_BOUNDARY / NOT_APPLICABLE / UNRESOLVED`，必须带 Evidence 或 Boundary。

## 3. Journey 理解
连续性维度（适用者检查）：首次使用 / 已有数据 / 重复使用 / 编辑重做 / 取消返回 / 中断 / 失败重试 / 刷新离开重开 / 部分完成 / 完成后 Next Job——真正改变路线的写入 Journey；其余关联 Behavior Contract。

### 首次使用理解（每个 P0 Job 应能回答）
```text
用户第一次从哪里开始？第一眼看到的主要任务是什么？
必须准备什么？哪些输入是可选的？主要操作控件是什么？
用户执行什么动作？动作之后界面发生什么？
什么情况下不能继续？用户如何知道下一步？
什么状态代表完成？失败时用户看到什么？
```

若关键项只能回答「源码里似乎…」「可能…」「根据组件推测…」，而 Runtime 可访问，则 Journey 记 `OPEN`，不得当作 fidelity contract，也不得把这种 DERIVED/INFERRED Journey 交给下游做保真依据。

### Journey Reality Facets（每条 P0/P1 Journey 应分别表达）
Baseline 应能分别说清这个 Journey 在五个 **Reality facet** 上各是什么状态（facet 定义与 Evidence 层规则以 `evidence-standard.md` §2 为唯一权威）：

```text
declared:     被声明/被意图成什么样？
implemented:  source 里有什么机制？
reachable:    用户能不能进到它？
executable:   当前环境里实际跑得通什么？
experienced:  用户实际看到与做到什么？
Gap:          它们在哪里分叉？
```

**这是五个 facet，不是五个等级**：不存在 `declared < implemented < … < experienced`，也不得写「该 Journey 已达到某一层」。facet 之间可以同时成立——`implemented` 且 `not experienced`（能力在代码里但流程中用不了）是合法且常见的结论。

允许各 facet 不一致，也允许某一个就是 Unknown。**把它们压成一份虚假自洽的「Current Product 描述」是禁止的核心失败模式**。

### Journey 深度轴（`P0/P1 且 UI-bearing`）
广度（Start→Success→分支走通）不足以证明体验层已被恢复。深度轴只登记 `P0/P1 且 UI-bearing` 的 Journey，每条给出三项判定：

```text
interaction          PRESENT | N/A(理由) | MISSING
presentation         PRESENT | N/A(理由) | MISSING
experience observed  PRESENT | MISSING
```

**无 UI 的 P0/P1 Journey 不登记**——它没有 interaction / presentation / experience 事实，不要为了凑表把它塞进深度轴。

`PRESENT` 的判据是**存在对应的 primitive**（`Kind: interaction` / `Kind: presentation` / `Reality: experienced` 且 Channel 符合 §2 适配表的 `E-*`），不是「Journey 散文里提到过」，也不是「源码结构看起来会这样渲染」。

**任一 P0/P1 UI Journey 出现 MISSING → 不得声明 `COMPLETE`**（可以是 `PARTIAL`，并把缺口登记为 Unknown）。深度轴只作用于 P0/P1 UI Journey：**禁止**把它扩到全部对象或全部 Surface——那会退回无差别 checklist 化。「哪些 P0/P1 Journey 属于 UI-bearing」是语义判断；机械检查只保证已登记行的记录完整性与其 J-ID 归属，不追补缺行。

> 本条修复的真实失败：旧规则曾在 `Channel: runtime` 且面向 UI 的 Evidence **数量为 0** 的情况下全绿收口。

### 目标范围内的完整性（复刻 / 重构）
当用户目标是产品复刻或结构性重构时，边缘路径不是核心路径的附属品，而是行为契约的一部分。必须恢复目标范围内的：

- 数据不完整、无数据、失效数据时的行为；
- 不同任务状态下允许的操作；
- 失败、取消、重试、恢复的状态转移；
- 权限、前置条件与业务约束；
- 跨模块、跨页面的对象与状态关系；
- 用户可能走出的分支、回退与退出路径；
- 当 Spec Target Scope 包含 backend / async / stateful 能力时：并发 / 竞态、幂等 / 重复提交、顺序 / 乱序、超时 / 退避 / 重试、部分失败 / 补偿 / 回滚、依赖降级 / 熔断、事务边界 / 一致性、限流 / 资源耗尽；不适用时写明 N/A 与理由。

可以从核心路径开始调查，但不能把核心路径完成当成整个任务完成；未观察或未验证的部分必须标记为 Unknown / Boundary，不得用推断填补。重构场景的完整理解不等于完整保留现状：旧产品的边缘行为可能应删除、合并或重新设计，但必须先理解其作用与影响。局部诊断不要求此完整性。这些行为应落到 `B-*` Behavior Contract，而不是只留在 Journey 或 Inventory 条目里。

## 4. 系统因果理解（Critical Flow Causal Sufficiency）
**Critical Flow** = 为实现核心产品能力而发生的系统因果过程（见 `modeling-rules.md` §1），与 Journey（用户实际经历的任务过程）平行。

每条 P0/P1 Critical Flow 结束时必须能回答五个问题：

```text
1. Trigger 是什么？
2. 核心对象是什么？关键状态如何变化？
3. 跨哪些模块？data/control 怎么流动？
4. 主要 failure / boundary 是什么？
5. 结果是什么？谁继续消费？
```

**这是理解充分性的判据，不是调查步骤。** 按什么顺序想、用什么路径查由模型自己决定；答不出来才是问题 → specific Unknown → 回到调查循环。

**Key Transition**（一旦记录为 Critical Flow 的关键 transition，就要求 Prediction + Verification）：

- 核心对象状态 transition
- 跨模块 data/control transition

Prediction → Verification 格式：

```text
Given: state S
When: action A
Predict: object X changes from X1 → X2, and triggers Y
Verify via: source trace / runtime observation / executable test
Result: CONFIRMED / CONTRADICTED / UNVERIFIED
```

没有可执行验证通道 → Prediction 仍然只是 hypothesis，不能作为关键 causal edge 的最终证明。不冒充 causal truth。

## 5. 收口前的复查
暂时不依赖当前 Task Map，重新扫一遍这些输入：

- unmapped / unresolved surfaces；
- core object lifecycle gaps；
- cross-domain handoffs；
- unknowns / contradictions；
- 主要代码/产品区域中当前 Jobs 没有解释的部分；
- **体验保真缺口**：对每个 P0/P1 Job，是否存在关键 user-observable step 仍只由 Source 推断、没有 Runtime / direct evidence 支撑？若有且 Runtime 可访问 → 缺口仍在。

若发现会改变 Product Model、P0/P1 Job、Journey 或关键 Behavior 的重大遗漏，**不允许直接补文档后收尾**，必须回到调查循环：

```text
Question → Evidence → Claim → Model/Coverage → 复查
```

只有**最后一次**复查不再出现新的高影响发现，才考虑收口。

## 6. Semantic Reconciliation（一致性）
Validator 检查结构完整性，但不能证明「整个系统解释语义上能够同时成立」。

例如：

```text
Flow A: Version immutable
Flow B: Iteration mutates current Version
```

两个 flow 五问都完整、references 都存在、没 Unknown、provenance 都合法，照样语义冲突。

收口前读取 P0/P1 Critical Flow views + relevant Experience Reality + unresolved contradictions，检查是否存在无法同时成立的 object/state/flow interpretation；发现冲突 → 继续调查；无冲突 → Design-ready。

**这是语义判断，不是机械检查。** Validator 不做这个判断。

## 7. Design Readiness（收口意味着什么）
允许标记 `COMPLETE` 前，以下都应成立（语义判断；任何一项不成立时保持 `IN_PROGRESS / PARTIAL / BLOCKED`，并把缺口写成具体 Unknown）：

- P0/P1 Critical Flow 能回答 §4 的全部问题；
- 每条 P0/P1 UI Journey 的深度轴已判定：`interaction` / `presentation` 为 `PRESENT` 或有理由的 `N/A`，`experience observed` 为 `PRESENT`；无 UI 的 P0/P1 Journey 不登记；
- 每条 P0/P1 Journey 已分别表达五个 Reality facet 与 Gap，未压成单一「Current Product」描述；
- 若目标是复刻或结构性重构，§3「目标范围内的完整性」所列边缘路径与状态关系已恢复，或已显式标记为 Unknown / Boundary；
- 若 Rigor 要求 Replica-Ready，还需满足 §8.3 全部条件；Replica-Ready 是 scope-relative 的更强完成判断，不由结构校验自动认定；
- Interaction / Presentation 事实存在于 `E-*`（`Kind: interaction` / `Kind: presentation`），不是只活在 Journey/Behavior 散文里；
- 高影响 Question 已 `ANSWERED`，高影响 Unknown / Contradiction 已解决或显式保留并写明影响边界；
- Inventory 无未处置项；核心对象生命周期已闭合或边界未知；每个 P0 Job 有完整 Start→Success Journey 并通过首次使用理解（§3）；
- Inventory COVERED 未被当作行为完整的替代：每个 in-scope item 的相关 `B-*` 已识别，且每个 `B-*` 的条件、状态、分支、副作用与异常路径已恢复或标记 Unknown；
- L1 Job 分类重新挑战过（它其实只是页面吗 / 内部流程吗 / 异常机制吗 / 另一个 Job 的步骤吗 / 同目标不同入口吗 / 与兄弟粒度一致吗）；
- 最后一次收口前复查（§5）没有新的高影响发现；Semantic Reconciliation（§6）成立。

**`Baseline Status = COMPLETE` 只表示调查已诚实收口，不表示被调查的产品完整。** 一份结论为「A 链路端到端成立、B 意图明确但执行断开、C 只有 source capability 无可达 UX、D 产品目的未知」的 Baseline 可以是 `COMPLETE`；反过来，把断口补成正常描述、把 Unknown 填成设计、或把 runtime 未观察的 UX 声称已确认，即使结构漂亮也不得 `COMPLETE`。

收口的正确标准是：「当前恢复的知识是否足以支持用户要求的下一步（**理解、诊断、设计、复刻或重构**）」**不是**「是否保存了足够信息让另一个 Agent 无源码重写一个等价系统」，也不是「Coverage 表是否填满」。后两者都是错误标准，不要用它们自我加压或用它们拒绝收口。

可执行时运行 `python scripts/check_baseline.py <baseline-output-dir>` 做结构校验；Structural Validation 不定义也不证明本文件的语义判据。

## 8. Replica-Ready 与依赖契约边界（scope-relative）
当用户目的是复刻或结构性重建，且 Rigor 要求实现规格时，以下规则相对于 Spec Target Scope 成立，不默认全产品。本节复用 Inventory / Coverage / Unknown Registry / Search Boundary，不新增平行 registry 或状态机。

### 8.1 Spec Target Scope 与 Spec Relation
- `Spec Relation` 相对于 **Spec Target Scope**，而不是 Baseline Scope：调查可以覆盖 Spec Target Scope 之外的依赖，但不自动纳入复刻范围。
- Inventory 记录必须包含 `Spec Relation: in-scope / dependency / out-of-scope`（字段定义见 `reconnaissance-protocol.md` §1）。
- `Spec Relation = in-scope`：Spec Target Scope 内的功能、系统能力、状态、接口、数据、副作用与异常路径；**即使不是独立 User Job，只要在 Spec Target Scope 内就必须处置**。
- `Spec Relation = dependency`：目标行为依赖的外部模块 / 服务 / 数据 / 外部系统。只需恢复**对目标行为有影响的契约**（接口、输入输出、状态、失败模式、前置条件、假设），**不要求理解依赖内部全部功能**；依赖契约完整性 ≠ 依赖系统内部完整性。
- `Spec Relation = out-of-scope`：与目标行为无关或用户明确排除；只记录边界，不要求 disposition。
- 跨边界调查允许：为理解真实依赖可以搜索 Spec Target Scope 之外的区域，但发现项按 Spec Relation 分类，**不自动纳入复刻范围**；调查广度 ≠ 复刻广度。

### 8.2 Discovery Audit
- Inventory 的发现必须有 executed 记录（工具 + pattern + 范围 + 日期），覆盖 Spec Target Scope 与必要依赖；只声明 declared 不得声称穷尽（复用 `evidence-standard.md` §4 Search Boundary）。
- 单链路 / 模块级 Spec Target Scope 的 discovery 只覆盖该链路 / 模块及其相关依赖，不是全产品 Inventory 扫描。
- Baseline Scope 可以大于 Spec Target Scope；超出部分用于理解依赖或背景，不自动成为复刻义务，但必须在 Baseline Scope 中如实记录。

### 8.3 Replica-Ready 完成标准
对选定 Spec Target Scope + Rigor=Replica-Ready，必须同时成立：

1. Discovery Audit executed（覆盖 Spec Target Scope 与必要依赖）。
2. Inventory 所有 `Spec Relation = in-scope` 与相关 `dependency` 项有 `Spec Disposition`（`COVERED / EXEMPT / OPEN`）；`OPEN` 项必须进入 Unknown Registry 并标明是否 replication-blocking；存在 replication-blocking OPEN 时不得判断 Replica-Ready 为「是」。
3. 每个 `Spec Relation = in-scope` 的 Inventory item 的相关 `B-*` 已识别；每个 `B-*` 的条件、状态、分支、副作用与异常路径有实现规格条目与可测试 acceptance；每个相关 `dependency` 有依赖契约。**Inventory COVERED 不等于行为契约已恢复；不新增 Feature Registry。**
4. 目标范围内的边缘路径、状态机、权限、校验、错误、后台 / 集成，以及适用时的并发、幂等、顺序、超时、补偿、依赖降级完整，或有显式 Unknown。
5. Runtime 确认按目标范围适用的证据通道：UI-bearing Journey 用 §3 深度轴，其他能力用 §4 关键转换与 runtime / test / data-snapshot 证据。
6. 无 replication-blocking unknown：任何影响 `Spec Relation = in-scope` 行为契约或 `dependency contract` 的未覆盖项都是 blocker，记录在 Unknown Registry（复用 Impact / Status），不得在存在 blocker 时判断 Replica-Ready 为「是」。
7. 实现规格一致：机器检查无 dangling `E-*` / `C-*` 引用；`J-*` / `B-*` 引用由语义审查确认；Evidence 变化后已重新核对并更新受影响节。
8. 诚实边界：声明 Spec Target Scope、与 Baseline Scope 的关系、dependencies、out-of-scope、Unknowns 与证据边界；不承诺无损源码重建。

是否达到 Replica-Ready 由实际规格充分性和阻塞缺口决定，**不能由文档数量、覆盖百分比或结构校验自动认定**。`check_baseline.py` 只校验确定性结构与引用关系，不声称检查行为覆盖或规格充分性。

### 8.4 与 Design Readiness 的关系
- `Baseline Status = COMPLETE` 表示完整 Baseline 内调查诚实收口；Replica-Ready 是相对于 **Spec Target Scope** 的更强完成判断，用于独立开发消费。
- **Replica-Ready Judgment 的单一来源是 `spec/INDEX.md`**；`BASELINE_INDEX.md` 只引用，不重复签发。
- 一个 Spec Target Scope 可以 Replica-Ready 但不是全产品 Baseline `COMPLETE`；也可以 Baseline `COMPLETE` 但未达到 Replica-Ready（若 Rigor 只是 Design-Ready）。
- 不满足 Replica-Ready 时，在 `spec/INDEX.md` 记录 blockers 与边界；用户决定接受部分、扩大 Spec Target Scope 或降低 Rigor。**不用百分比表达**。
