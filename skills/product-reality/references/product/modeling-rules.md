# Product / User Job / Journey 建模规则

**适用范围**：本文件约束建立持久 `product/` 模型时的 Product Model / Job / Journey / Behavior / Spec 表达；不定义调查入口、深度或完成标准。

## 1. Product Model
`product-model/` 只描述当前系统结构事实：领域、Surface、Core Object、状态所有权、依赖/Handoff、Supporting/Admin/Legacy 区域。不要在这里写长 Journey 或源码审计日志。

**Core Object 与模块划分的来源必须综合，不得由单一通道决定**：

```text
User Job + Runtime Experience + Product Intent + Entity lifecycle + Source capability + Reference evidence
```

明确禁止两条捷径：

- `Database / API entity → Product entity`：持久化模型是实现细节，不是产品概念；
- `当前一级导航 → Target product modules`：当前导航可能只是历史堆积。

若 `Session` 之类只是 implementation object，**不得因为数据库里有它就自动把产品组织成 session manager**。判断依据是「用户在语言里是否用它指代一件事、Job 是否需要它、runtime 里用户是否接触它」；不确定时记 Unknown，不要靠 schema 猜产品概念。

### Critical Flow（系统因果过程）
**Critical Flow** = 为实现核心产品能力而发生的系统因果过程。

与 **Journey**（用户实际经历的任务过程）平行，不是同一个东西：

```text
Critical Flow:
Version → TestRun → Evaluation → Comparison
（系统如何工作）

Journey:
Store → Detail → Test → Select → Run → Comparison
（用户如何经历）
```

**它们的错位就是设计信号。**

Critical Flow 记录在 `behavior/` 或 `product-model/` 中，引用 `E-*` / `C-*` ID。每条 P0/P1 Critical Flow 必须通过 Causal Sufficiency（五问，见 `coverage-and-readiness.md` §4）。

## 2. L1 User Job 判定
Candidate Job 必须通过：

1. 有清晰用户结果；
2. 有 Trigger；
3. 有用户可观察 Success；
4. 去掉页面名、模块名、API 名仍成立；
5. 不是另一个 Job 的步骤/入口/控制/失败分支；
6. 与同层兄弟 Job 粒度一致。

命名优先「动词 + 用户结果」：创建可用技能 / 验证候选方案 / 发布并消费资产，而不是 Pipeline / Store / History。

## 3. 分类
|现象|默认分类|
|---|---|
|用户为得到独立结果主动发起|User Job|
|一个 Job 中的必要操作|Journey step|
|Landing / Tab / Route|Surface|
|Search / route / queue / model loop / background stage|Internal workflow|
|Stop / retry / autosave / conflict / error|Behavior / cross-cutting|
|Settings / admin maintenance|Supporting/Admin，除非它本身是核心结果|
|旧链路/无消费代码|Legacy/Dead，不能自动提升为 Job|

## 4. Job 合并/拆分
合并：目标相同、Success 相同，只是入口/输入来源不同。
拆分：成功条件、生命周期意义、用户决策或后续 Job 明显不同。

## 5. Journey（derived view）
Journey 是**对 primitive 事实的消费视图**：只记录会改变用户下一步的「用户动作 + 关键系统反馈」，引用 `E-*` / `C-*` ID。

**Journey 不承载 Product Reality 的全部**：界面实际如何变化（状态转换、可见 mutation、阻塞与反馈时机）与界面结构长什么样（skeleton、morphology、分组、层级、density）属于 primitive，按 `Kind: interaction` / `Kind: presentation` 记入 `E-*`（定义见 `evidence-standard.md` §10）。同一条 Journey 可以对应完全不同的 Interaction 与 Presentation——只保存 Journey 会让两个本质不同的产品塌成同一个表示。

每个 P0/P1 Journey 固定：`Goal / Trigger & Preconditions / Start / User Action + Key Feedback / Success / Meaningful Branches / Next Job / Claim refs / Confidence`。

只记录改变用户下一步的事件。自动内部链路压缩；用户必须等待、选择、批准、恢复、理解不可逆状态时才展开。

**区分两种序列，不得互相冒充**：

- `System stage sequence`：需求→生成→质检→审核→产出 这类**执行阶段**，source 可推导，回答「系统内部按什么顺序发生」。
- `User experience sequence`：用户在哪个界面、看到什么、操作哪个控件、界面如何响应，回答「用户实际怎么完成这件事」，**需要 runtime 证据**。

`Start` 与 Journey 步骤的主语必须是用户动作（例：「在产线页底部 composer 输入一句话需求」），不得填成系统阶段名（例：「需求 → 生成」）。后者属于 System stage sequence，应留在 `behavior/` 或 product-model；把它写进 Journey 会让下游以为已经知道用户怎么开始。

**Replication / fidelity 场景的可观察字段**——可选，只填 runtime 实际观察到的；无证据时留空并转 Unknown，禁止用 source 推断填充：

```text
Entry State / Primary Interaction Primitive / Required Inputs / Optional Inputs
Visible Feedback / Blocking Condition
Completion Signal / Failure Signal / Key Information Hierarchy
```

Primary Interaction Primitive 用自然语言准确描述实际界面原语即可（composer-first / session-list-first / file-tree workspace / asset-card center / diagnostic cards / management table / wizard / canvas / timeline 等），**不建立固定 taxonomy**。这类差异是 **interaction model 差异，不是视觉差异**——同一 capability 与数据模型可以支撑完全不同的 interaction model。

## 6. Behavior Contract
属于实现保真但不是 Job 的信息放 `behavior/`：持久化、状态机、门禁、默认动作、副作用、快照/实时引用、失败恢复、权限、删除可逆性、并发冲突、刷新重开、对象创建/修改/删除、save/autosave/draft、async/background、stop/interruption/resume/retry、角色权限、失败/部分成功/恢复、跨 Job 副作用、默认值与自动动作等。

每条重要 Contract 至少记录：

```text
ID / Related Job / Trigger / Observable Behavior / State or Side Effect /
Failure-Recovery / Claim refs / Confidence
```

`Claim refs` 指向 canonical Evidence；`Confidence` 取值与语义见 `evidence-standard.md` §4。

## 7. Cross-Job Handoff
一个 Job 创建/修改的对象或状态被另一个 Job 消费时，明确记录：Producer Job / Object-State / Handoff Condition / Consumer Job / Snapshot-or-Live / Replication Impact。

## 8. 优先级
- `P0`：缺失后主价值闭环不能完成。
- `P1`：高频/高价值，缺失会明显降低可用性或关键决策质量。
- `P2`：辅助、配置、低频、旧链路。

优先级对象是 Job/Journey，不是页面。

## 9. Spec Projection（Replica-Ready）
`spec/` 是 derived view，但可承载完整开发级语义；每个重要结论必须可追溯到 `E-*` / `C-*` / `J-*` / `B-*`。装配规则：

- `spec/INDEX.md`：**Spec Target Scope**、与 **Baseline Scope** 的关系（equal / subset / diverged + 理由）、Dependencies & Boundaries、Replica-Ready Judgment（是/否 + blockers 引用 `U-*`）、证据边界。Replica-Ready Judgment 只在 `spec/INDEX.md` 签发；`BASELINE_INDEX.md` 只引用。
- Behavior Contracts：从 in-scope Inventory + `B-*` 投影；每个 in-scope Inventory item 的相关 `B-*` 必须列出；每个 `B-*` 的条件、状态、分支、副作用与异常路径进入 spec。不新增 Feature Registry。
- interfaces / data-model / state-machines / permissions / validations / background-jobs / integrations：从对应 `E-*` 投影（由 Subject / Locator / Observation 表达的接口 / 数据 / 状态 / 权限 / 校验 / 后台 / 集成事实；`Kind` 仍只使用 `interaction / presentation / intent`，其余留空）。
- dependencies：只写对目标行为有影响的契约（接口、输入输出、状态、失败模式、前置条件、假设），不写依赖内部全部功能；引用 `E-*` / `C-*`。
- acceptance：按 `B-*` 组织，每个 `B-*` 至少一条可独立验证的验收条件；Acceptance Criteria 表是唯一 acceptance 来源。这是规格充分性的语义判断，由模型决定，不由 validator 强制。
- 系统级行为（适用时）：并发 / 竞态、幂等、顺序 / 乱序、超时 / 退避、部分失败 / 补偿、依赖降级必须进入 spec；不适用写 N/A 与理由。
- Evidence 变化后必须重新核对并更新受影响节；不声称自动重生。
- 小 Scope（单链路/模块）可以用单个 `spec/<scope>.md` 承载全部节；大 Scope 可拆分为家族文件。不强制初始化全套 Baseline 产物。
