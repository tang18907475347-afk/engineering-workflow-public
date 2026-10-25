# Investigation Question 设计
**适用范围**：本文件用于设计调查问题与停止条件；不定义调查深度，也不要求每次调查都建立 Question Ledger。轻量调查可以直接回答，当前问题闭合即停。

大型逆向最容易退化为「把仓库尽可能扫完」：产生大量上下文，却不一定增加对用户任务与系统行为的理解。Question 的作用是限定：**我们为什么看这一段，以及什么证据足以停止。** 好问题直接指向因果理解——对象如何变化、状态如何跨模块衔接、失败在哪里断开、用户实际经历什么。

## 好 Question 的标准
一条 Question 应满足：

- 回答后会影响 User Job / Journey / Behavior / Object Lifecycle / Handoff / 系统因果解释 / 复刻边界中至少一项；
- 能定义 Required Evidence；
- 能定义 Search Boundary；
- 能判断何时 `ANSWERED / PARTIAL / BLOCKED`；
- 不只是「这个目录里有什么」。

## Question 类型
|类型|典型问题|
|---|---|
|Job|用户为什么进入这个区域？成功结果是什么？|
|Journey|从真实起点到成功要经过哪些用户动作与关键反馈？|
|Behavior|某动作后真实状态如何变化、如何恢复、是否持久化？|
|Object|谁创建/读取/更新/删除这个核心对象？|
|Handoff|Job A 产生的对象/状态如何被 Job B 消费？|
|Reachability|某能力是当前可达、隐藏可达、legacy 还是 dead？|
|Negative|是否真的没有编辑/删除/恢复入口？在哪个边界内成立？|
|Contradiction|UI、源码、测试、文档为什么给出不同答案？|
|**Experience**|用户实际看到什么、第一次从哪里开始、主要界面原语是什么、操作后界面如何响应、怎么知道完成或失败？|
|**Intent**|这个 Demo 最终想证明什么核心价值？哪些 Surface 是真实产品概念，哪些只是演示 / 临时实现 / 历史遗留？|
|**Completeness**|这条 P0/P1 Journey 端到端跑通吗？断在哪一层（Intent / Implemented / Executable / Experienced）？|

## Product Intent 重建（半成品 Demo 中是一等调查对象）
Current Implementation 不能可靠代表 Product Intent，因此必须主动重建。至少回答：

```text
这个 Demo 最终想证明什么核心价值？核心用户是谁？
用户真正想完成什么 Job？哪 3–5 条 Journey 属于产品目标？
哪些 Surface 是真实产品概念？哪些只是演示 / 临时实现 / 历史遗留？
哪些能力明确没有完成？哪些设计是 Target Intent、哪些只是当前实现？
```

不能回答时保持 Unknown，**不得为了结构完整强制猜**。Intent 结论复用现有 provenance / Confidence 语义表达（Confirmed / Probable / Unknown / Conflicting），**不新增 enum**。

## Experience Question 的 Required Evidence
用户可观察体验类 Question 的 Required Evidence **不能只写 source/docs**：source 与 docs 无法互相确认出「用户实际看到什么」。需要 runtime 直接观察——截图、DOM、walkthrough、录屏。

**观察点由 User Job 驱动，不由页面数量驱动**。每条 Journey 只取少量高信息量状态：

```text
Entry → Required input / prerequisite → Primary action
→ 重要状态转换 → 决策 / 阻塞点 → 完成或失败
```

禁止「把所有页面全截图一遍」、hover / tooltip / modal / edge state 的穷举采集。

触发与否的判断（必触发 / 按需 / 不强制）以 SKILL.md「Runtime Experience Observation」段为准，本文件不重复定义。

## Required Evidence
Question 创建时先想清楚：什么证据能在声明边界内回答它。例如：

- `runtime + source`：验证「点击后立即持久化」。
- `all write sites within service + tests`：验证对象更新语义。
- `route registry + UI entry + handler`：验证当前可达性。
- `API/client/service/tests`：做 bounded negative search。

Required Evidence 是目标，不要求机械凑齐所有证据类型；一类证据已足以证明结论，就停止扩展。

## Question Ledger
使用 `assets/question-ledger.template.md`。每个 Question 至少记录：`Q-ID / Question / Decision Impact / Required Evidence / Search Boundary / Status / Answer Claim refs / Open U-ID`。

## 停止规则
Question 在声明边界内得到足够证据时停止，Claim 已落盘即算回答。只有出现具体 gap 才继续扩大范围；禁止因为仓库还有很多文件就继续搜索。
