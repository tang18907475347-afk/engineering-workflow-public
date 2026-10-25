---
name: product-reality
description: 用于代码机制调查、跨文件业务链路、状态与 owner 追踪、为某个需求理解现状（需求级现状摘要 reality.md）、产品行为 / 用户路径重建、复刻或结构性重构所需的现状理解，以及证据与覆盖边界判断。不用于目标体验设计或工程实现。
---

# Product Reality

## Runtime Contract
- **Outcome**：在当前证据边界内回答「系统现在是什么、为什么这样运行、用户实际经历什么」。
- **Done**：当前问题所需的代码机制或产品事实已被证据支持，边界已说明。
- **Next consumer**：Product Design、Implementation Strategy、Test Readiness Review、Coding Agent。
- **Stop**：不设计目标态、不制定工程方案、不实现代码；不把每个问题都升级成完整 Baseline，也不把最小调查当成默认工作形态。

## 先分流：这次是哪条路径
按用户目的选路径，而不是按 Skill 被激活这件事本身。三条路径的证据纪律相同，差别只在完整性边界与产物：

|用户目的|路径|产物|
|---|---|---|
|代码问题：某个行为在哪里实现、谁拥有、调用链、状态写入、失败分支|**轻量 A：代码机制**（下文）|直接回答；通过准入的昂贵事实写入 `intelligence/`；零写入是合法结果|
|为某个需求理解现状，供设计、实施计划、提测审查使用|**轻量 B：需求级现状摘要**（下文）|`.engineering/requirements/<req>/reality.md`|
|系统 / 模块 / 业务域级理解、复刻、迁移、审计、结构性重构，或需要 Coverage、Design Readiness、Replica-Ready 判断|**深度模式**|`product/` Baseline 或 `spec/`；**先完整读完 [references/product/deep-mode.md](references/product/deep-mode.md)**|

- 用户目的不明确、且不同路径会导致明显不同的工作量时，说明你的判断并让用户确认；能唯一推断就直接走。
- 轻量路径中发现局部问题的根因跨越模块时，主动扩大调查，不被「局部」标签限制；但如果目标本身变成了复刻、重构或完整理解，说明理由并经用户同意后再转入深度模式。
- 先读 `.engineering/context.md`（业务上下文，如有）：它告诉你业务词在代码里叫什么、哪些规则不能违反、过去哪里理解错过。没有这个文件不影响调查。

## 两种知识形态
同一套系统可以有两种理解产物。它们服务不同消费者，允许引用同一段源码：

|产物|回答什么|形态|消费者|
|---|---|---|---|
|`.engineering/intelligence/`|代码机制：owner、调用链、dataflow、协议差异、失败分支、检索路径|按业务模块分片的代码事实缓存；front matter + section + locator|任何工程 Skill；可整目录删除重建|
|`.engineering/product/`|产品现实：Jobs、Journeys、Behavior、系统因果、UX facets、覆盖边界|`E-*` 证据 + Claim + derived view + Coverage|Product Design、IS、TRR|

**来源重叠不等于知识重复。** 同一段源码可以同时支撑一条代码机制缓存和一条产品证据；前者关心「改哪里」，后者关心「它证明了什么产品行为、证据边界是什么」。不强制两种产物使用同一 schema，也不要求只保存一份。

需求级现状摘要 `reality.md` 不是第三种知识：它是面向一个需求的**派生视图**，只引用上面两种产物或源码中的定位，不另立事实。

## 核心不变量（两条路径共用）
编号沿用原编号；1–4、12、13 是产品建模不变量，见 [references/product/deep-mode.md](references/product/deep-mode.md)。

5. **先还原现状，再谈优化**——不得在本 Skill 内删除步骤、重构流程或提出新版 UX。
6. **证据先于信心**——「看起来合理」「已经认真检查」「文档很长」都不是证据；证据通道受执行环境限制时如实标注。
7. **Coverage 必须有边界**——「未发现」只能在明确检查范围内成立；没有覆盖不能写成不存在。
8. **未知必须显式存在**——高影响 Unknown 未解决时不得声明收口（Status 保持 `IN_PROGRESS / PARTIAL / BLOCKED`）。
9. **调查由高价值问题驱动**——问题必须指向会改变系统 / 体验理解的东西；禁止为了填满 Coverage 表格做无目的扫描。
10. **人类不做信息搬运**——能直接从系统、代码、测试、文档、历史产物中获取的信息由执行者自行获取。
11. **Demo 是 Evidence Source，不是 Ground Truth**；一条事实只描述它所对应的那个 Reality facet：`declared / implemented / reachable / executable / experienced`。这是五个 facet，不是五个等级——禁止 ordinal 推导，也禁止四条冒充：Intent exists → 当前产品支持；Source exists → Runtime 可执行；Runtime 可执行 → UX 完整；UI exists → Journey 完整。

## 轻量 A：代码机制
代码机制缓存回答「这个行为在哪里实现、谁拥有它、改动会触达什么」。四条不变量：
1. **只缓存昂贵事实**：一次 grep / symbol / 单文件能恢复的不记。
2. **事实与 owner 闭合**：证据必须落在能直接证明它的文件 / symbol；跨文件语义用 `- calls →` 指向真实 owner。
3. **每条事实可重新核验**：locator 优先 `file + symbol`，其次源码原样出现的 `search:` 字面量；不用行号、AST path、fingerprint 作为 identity。
4. **不制造完整性幻觉**：intelligence 没写不等于仓库不存在；关键失败分支没追到就写 `[failure path not captured]`。

取舍只有一条：**宁可 miss，不可误导。** 缓存可以整目录删除重建；它不是 canonical 产品证据。CRUD、写入门槛与文档结构见 `references/code/intelligence-contract.md`、`references/code/extraction.md`、`references/code/intelligence-format.md`。

收口：当前问题闭合即停；命中不足就回源码，不做负向存在性判断。

## 轻量 B：需求级现状摘要（reality.md）
**为什么需要它**：设计要从用户实际走过的路径里找痛点，实施计划要知道改动会碰到哪些现有行为，提测审查要知道该回归检查什么。这三件事来自同一次调查；写成一份小而稳定的摘要，下游就不必各自重新调查，也不必读懂整套 `product/` schema。

**产物**：`.engineering/requirements/<req>/reality.md`，格式见 [assets/reality.template.md](assets/reality.template.md)。需求必须显式指定或唯一可推导；有多个候选时列出并请用户选择。

**内容来源**：
- 已有相关的 `product/` Baseline 时，它是 Baseline 的投影：挑出与本需求相关的部分，引用 `E-*` / `J-*` / `B-*`，不复制正文；投影时仍按当前源码核对你依赖的那几条。
- 没有 Baseline 时，它就是本次轻量调查的结果：按「轻量 A」的方式追调用链，每条事实给出 `文件#符号` 定位，查起来贵的事实照常写入 `intelligence/`。
- 两种来源产出的形状相同，下游不需要关心它是怎么来的。

**写好它的标准**：
- 「用户实际路径」写用户真正看到与经历的：每一步看到什么、要做什么决定、要等多久、可能在哪出错。能运行就运行（运行时证据），不能运行就标明是源码推断——不把「代码里有」写成「用户体验到」（不变量 11）。
- 「已观察到的问题」只写现象与证据，不写方案；它是交给设计找痛点的原料，不是本 Skill 的设计结论（不变量 5）。
- 「候选的不能破坏的行为」是候选，由设计或实施计划确认后才进入 Workspace 的 Preserve；本 Skill 不替下游决定什么必须保留，现状也不自动成为约束。
- 头部写明基于哪个 commit、来源是 Baseline 投影还是直接调查，以及「这是现状，不是期望」。
- 只写当前需求真正涉及的范围；调查广度服从问题闭合，不为填满模板扩大范围。

**维护**：由本 Skill 写；下游只读。下游使用中发现事实错误或过期，按 `references/evidence-and-correction.md` 回到这里原地修正，不在下游另写一份。

## 深度模式
需要时，先完整读完 [references/product/deep-mode.md](references/product/deep-mode.md)。调查契约（Scope、Rigor、Replica-Ready）、产品建模不变量、Runtime Experience Observation 与收口规则都在那里，规则与原来完全一致；`scripts/check_baseline.py` 只在深度模式下运行。

## 工作区
```text
.engineering/
├── PROJECT.md                  # 导航，不是状态机
├── context.md                  # 业务上下文（跨需求，见 workspace-and-ownership）
├── product/                    # canonical 产品现实（深度模式）
├── intelligence/               # 可丢弃的代码机制缓存
├── requirements/<req>/reality.md   # 需求级现状摘要（派生视图）
└── work/                       # scratch，不得被 canonical 结论引用
```

- 从当前工作目录向上找最近的 `.engineering/`；找不到时以 Git worktree 根为候选项目根。
- 启动时只读 `PROJECT.md` 与当前问题相关的 1–2 个入口，不预加载整个 Baseline。
- canonical 结论不得引用 `.engineering/work/` 或 `/tmp`。
- 判断工作区归属或准备写入时，以 `references/workspace-and-ownership.md` 为唯一权威；事实修正见 `references/evidence-and-correction.md`。

## Reference routing
|当前问题|读|
|---|---|
|看不懂某个术语（Status、Basis、Binding、五个面、Scope / Rigor、AC / P 等）|[references/glossary.md](references/glossary.md)|
|代码行为、owner、调用链、状态写入、失败分支|先按本 SKILL.md 的代码机制规则；缓存 miss 或需要写缓存时再读 [references/code/intelligence-contract.md](references/code/intelligence-contract.md)|
|需要判断什么值得缓存、owner 落在哪、契约与失败分支怎么抽|[references/code/extraction.md](references/code/extraction.md)|
|需要写 intelligence 文档：结构、locator / relation / 分片|[references/code/intelligence-format.md](references/code/intelligence-format.md)|
|抽取质量漂移、owner 归属混乱，或不确定某类事实是否值得缓存|[references/code/worked-example.md](references/code/worked-example.md)|
|不确定当前问题是否值得调查、需要多少证据、何时停止|[references/product/investigation-questions.md](references/product/investigation-questions.md)|
|需要判断工作区归属、写入位置或准备写入|[references/workspace-and-ownership.md](references/workspace-and-ownership.md)|
|事实被修正、旧结论失效，需要判断影响范围|[references/evidence-and-correction.md](references/evidence-and-correction.md)|
|涉及决定状态、Binding 或 handoff 语义|[references/delivery-and-handoff.md](references/delivery-and-handoff.md)|
|进入深度模式：完整 Baseline、复刻、迁移、审计、结构性重构、Coverage / Design Readiness / Replica-Ready|先完整读 [references/product/deep-mode.md](references/product/deep-mode.md)，再按其中的 routing 读取|
|写需求级现状摘要|[assets/reality.template.md](assets/reality.template.md)|
|业务上下文的写入规则（纠偏记录、准入）|[references/workspace-and-ownership.md](references/workspace-and-ownership.md)|

## 禁止
- 禁止把代码调查默认升级成完整产品逆向，或反之用缓存冒充产品证据。
- 禁止把静态源码推断写成 runtime 已观察事实。
- 禁止把五个 facet 当等级排序，或为 Interaction / Presentation 新建 ID namespace。
- 禁止在本 Skill 内做目标设计、UX 优化或工程实现。
- 禁止宣称 Baseline 足以替代 Reference Source。
