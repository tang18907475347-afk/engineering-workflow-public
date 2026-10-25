<!-- Generated from shared/delivery-and-handoff.md by scripts/sync_shared_references.py. Do not edit this copy directly. -->
# Delivery and Handoff
本契约区分产品决定、工程 Binding 与可调整空间；证据和格式本身不产生授权。

## 1. 决定记录
一个产品/设计决定至少包含：

```text
Decision-ID: D-<n>                 # project 内唯一，可选但推荐
Statement: <决定本身>
Status: PROPOSED | ACCEPTED | SUPERSEDED
Basis: DECISION | EVIDENCE | DERIVATION | DESIGN_JUDGMENT
Authority: <user / product-owner / design-owner / ...>
Accepted-At: <date>                # Status=ACCEPTED 时填写
Scope: <这次接受覆盖到哪里>
Basis-Ref: <E-* / C-* / 上游决定 / 设计判断>
Derived-From: <已接受的 D-* / 约束>   # Basis=DERIVATION 时填写
Supersedes / Superseded-By: <D-*>
```

**`DERIVED` 不是 Status。** 一个推导出来的结论本身也可能处于 `PROPOSED` / `ACCEPTED` / `SUPERSEDED`。推导只说明它怎么来的，不自动赋予产品权威。

### 1.1 什么可以成为 Binding
只有以下之一可以进入工程的 Binding：

1. **已被明确接受**：`Status: ACCEPTED`，`Basis: DECISION`，有 `Authority` 与 `Accepted-At`。
2. **由已接受约束必然推出**：`Status: ACCEPTED`，`Basis: DERIVATION`，`Derived-From` 指向一个已接受决定，且推导是**严格必要**的（没有它，被接受的约束无法成立）。必须是可说明的最小必要项；凡是增加用户可见行为、体验取舍或实现选择的内容，默认不是严格必要。
3. **已接受决定的 Preserve / Verification Obligation**：由接受决定直接定义的保护项或验证义务。

以下不能成为 Binding：

- 只是 `PROPOSED` 的设计提案；
- `Basis: DERIVATION` 但只是“合理推导”“通常这样做”，不是严格必要；
- `Basis: DESIGN_JUDGMENT` 且没有用户/授权人接受；
- Agent 自己认为更好的方案。

P4' 例：用户接受“详情默认抽屉”，不代表接受“必须支持深链、返回后恢复滚动位置”。后者应记为 `PROPOSED` / `Adjustable`，除非用户明确接受，或它确实是“抽屉默认打开”这一约束的严格必要项。不要把设计含义自动升级为产品要求。

### 1.2 决定记录在哪里
- 决定记录在**接受发生的地方**：Clarification、Design、Workspace 或模块记录。
- 另一侧只链接/引用，不复制一份新的权威。
- 跨侧引用使用 `Decision-ID` 或路径 + 小节锚点。
- 决定被替换时，更新 `Status: SUPERSEDED` 与 `Superseded-By`；不删除历史，不自动传播到所有下游。

## 2. Handoff 何时需要
Handoff 是**跨能力的信息传递**，不是审批单，也不是每个任务的必填产物。

**只有在存在真实下游消费者，并且需要知道“工程当时消费的是哪个设计版本”时，才发布不可变 handoff 快照。** 例如：

- 设计在一个上下文完成，工程在另一个会话/任务中实现；
- 多个模块或多人并行，需要锁定同一份设计决定；
- 设计决定可能在被消费后继续演化，必须能追溯旧版本；
- TRR 需要按一份明确的设计 acceptance 做独立验证。

以下情况**不需要** handoff 快照、ID 或 supersede 链：

- 简单的 UI 修改、局部样式调整；
- 设计、实现、验证在同一上下文连续完成，消费者就是当前任务；
- 没有跨能力消费者，设计记录本身已经足够。

不要为了制度完整创建空 handoff。没有 snapshot 时，`design/` 中的当前有效决定就是来源；消费者直接引用即可。

## 3. 不可变快照
需要 snapshot 时：

```text
design/module-handoffs/<module-id>/<handoff-id>.md
```

- `<handoff-id>` 推荐 `YYYYMMDD-N`（按日期可排序、同一天多个用 `-N` 区分）。ID 一旦发布不复用。
- **内容不可变**：已发布的 handoff 正文不再原地改写。
- **生命周期元数据可变**：`Status`、`Superseded-By`、`Superseded-At` 可以更新。
- 新设计决定需要改变 handoff 内容时，发布新的 handoff-id，并把旧 handoff 标 `SUPERSEDED`；旧快照保留。
- 消费者记录自己消费的精确 `handoff-id`；不要只写“看过设计”。

Handoff Status：

- `READY`：可供下游消费；
- `BLOCKED`：存在具体 blocker，尚不能作为可靠输入；
- `SUPERSEDED`：已有更新版本，旧快照只用于追溯。

`BLOCKED` 必须有具体 blocker；不能因为“设计还不够完整”泛化阻断简单任务。

## 4. Handoff 内容
```text
# Module Handoff: <module-id> / <handoff-id>

- Status: READY | BLOCKED | SUPERSEDED
- Superseded-By / Reason:
- Consumer Record: <由消费者填写：任务 / 日期 / 消费的 handoff-id>

## Problem / Intent
这个 surface 要替用户解决什么，本轮为什么动它。

## Binding
### Accepted Decisions
- D-* / Statement / Authority / Accepted-At / Scope
### Strict Derivations
- D-* / Derived-From / 为什么是严格必要
### Preserve
- 已接受决定中不能被破坏的行为、语义或约束
### Verification Obligations
- 必须证明什么；不规定具体测试实现

## Adjustable
### Proposed Design Choices
- D-* / Status: PROPOSED / Basis
### Open Questions / Dependencies
- 仍允许工程层探索的问题；被 PHASE 挡住的结构问题

## Relevant Evidence
- E-* / C-* / B-* / 路径 + 小节；不重抄长证据

## Hard Constraints
- 真正不能违反的条件，逐条写依据
```

`Binding` 与 `Adjustable` 必须分开。下游不需要猜“哪些是已确认要求、哪些是可以调整的设计判断”。

## 5. 消费与失效
- 消费者先读当前 `PROJECT.md` / `design/` 入口，确认是否有相关 handoff。
- 有 handoff：记录精确 `handoff-id`，只读与当前任务相关的小节。
- 没有 handoff：直接读 `design/` 当前有效决定；不要求补建 snapshot。
- 已消费的 handoff 被 `SUPERSEDED` 时，检查**相关性范围**：被引用的 `ACCEPTED` 决定、`Preserve`、`Verification Obligations`、相关 `E-*` / `C-*` 是否发生实质变化。
- 无关变化不阻断；只有当前交付依赖的内容变化才需要重新协调。
- 引用变化是线索，不是唯一信号：新发现的、此前未被引用的关键事实也可能影响当前交付；发现者应记录并触发相关范围检查。
- 不自动把旧 handoff 的所有下游标为失效，不建 propagation 图，不要求全量重算。

## 6. 状态轴
不同状态回答不同问题，不能互相推导：

|状态|回答的问题|谁维护|
|---|---|---|
|Baseline `IN_PROGRESS / PARTIAL / COMPLETE / BLOCKED`|当前现实调查是否诚实收口|Reality|
|Handoff `READY / BLOCKED / SUPERSEDED`|设计信息是否可供下游消费|Design|
|计划 `提测条件就绪 / DONE`|实施计划自己的交付条件是否满足|Implementation Strategy|
|`READY_FOR_TEST / BLOCK`|独立交付审查是否证明达到提测条件|TRR|
|`PASS — CODE / DOM / INTERACTION / VISUAL / NOT VERIFIED`|实际验证到了哪一层|执行验证的一方|

- `COMPLETE` 不等于产品完整；`DONE` 不等于 `READY_FOR_TEST`；`PASS—INTERACTION` 不等于所有验收项已证明。
- 不建立 `PASS` → TRR 状态的映射表。

## 7. TRR 的证据语义
TRR 对每个 Expected 回答四件事：

1. **Expected**：按已接受目标/决定，应该发生什么。
2. **Evidence Required**：要证明它，至少需要什么类型的证据（源码、DOM、交互、视觉、运行时、测试）。
3. **Evidence Available**：实际拿到了什么；来源、范围、可重放性。
4. **Proven**：这些证据实际证明了哪一部分；不能证明的部分明确标出。

`PASS` 是**证据描述**，不是证据要求：

- `PASS — CODE`：代码存在/路径成立；不能证明可达、可执行或体验正确。
- `PASS — DOM`：渲染结构成立；不能证明交互结果或视觉质量。
- `PASS — INTERACTION`：实际交互路径成立；不能证明所有状态、所有入口或视觉保真。
- `PASS — VISUAL`：在给定视口/环境下视觉成立；不能证明其他视口、状态或设计意图。
- `NOT VERIFIED`：没有足够证据；不自动等于失败。

TRR 独立判断证明范围，不把设计侧的 `PASS` 直接当作自己的结论。设计侧验证记录可以作为 `Evidence Available` 输入，TRR 仍需判断它是否覆盖当前 Expected。

## 8. 阻断与不阻断
可以阻断（`BLOCK`）的情况：

- 已接受 scope 内缺少必需的 Evidence，且无法在当前交付中补足；
- 实际交付偏离了 `ACCEPTED` 决定，且未获授权改变；
- 存在未解决的关键冲突，导致无法形成 Expected；
- 无法确定当前有效的接受目标（例如 handoff 被 supersede 且新版本未就绪）。

不应自动阻断的情况：

- 产品现状中发现了未纳入当前 Requirement 的体验缺口；
- 无关的 Baseline / Design 变化；
- 旧 handoff 被 supersede，但当前交付不依赖其变化部分；
- 设计侧 `PROPOSED` 项尚未被接受，但当前交付不依赖它。

产品体验缺口是否影响当前交付，取决于它是否属于**当前已接受的交付目标**，不取决于它是不是 P0。不能把所有产品缺口自动升级为当前 Requirement 的 P0 Blocker。
