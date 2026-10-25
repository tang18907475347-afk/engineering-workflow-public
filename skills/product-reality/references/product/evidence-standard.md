# Evidence / Claim / Unknown 标准

**适用范围**：本文件只约束写入 `product/` 的持久证据与 Claim。轻量回答与 `intelligence/` 缓存不使用这套 schema；不要因为读过本文件就为一次性结论创建 `E-*` / `C-*`。

## 1. 稳定 ID 与分层
- `E-xxx`：Evidence —— **唯一的 primitive fact 类型**
- `C-xxx`：Claim —— 对 E-\* 的综合（derived）
- `J-xxx`：User Job / Journey —— derived view
- `B-xxx`：Behavior Contract —— derived view
- `Q-xxx`：Investigation Question
- `U-xxx`：Unknown

**分层是架构事实，不是排版约定**：

```text
E-* primitives
   ↓
C-* Claims
   ↓
Product Model / Journey / Behavior / Coverage   ← synthesis / projection（消费视图）
   ↓
Diagnosis → Design
```

`product-model/`、`task-map/`、`behavior/`、`coverage/` 一律是 **derived view**：它们引用 primitive ID，**不是 Product Reality 本身**。任何「Journey/Behavior 已经写了，所以事实已保存」的想法都是错误的——它们会为了可读性压缩细节，被压缩掉的部分必须仍然能在 `E-*` 中找到。

**禁止新增 primitive ID namespace**（如 `IT-*` / `PM-*`）：事实类型由 `Kind` 字段表达，所有 primitive 都是 `E-*`。

ID 一旦发布不复用，在同一 `product/` 内唯一；下游通过产品路径 + ID 引用，其他区域的观察可直接引用持久路径，不维护全局 E / C 注册表。跨文件引用而不复制长证据；适用边界见 skill-local `references/evidence-and-correction.md`。

## 2. Evidence：E-ID + 七字段（8 列）primitive schema
Evidence 是可定位的原始依据。每条 Evidence 记录由 `E-ID` 与七项内容字段组成（共 8 列），**无隐式默认值**：

|字段|回答什么|取值|
|---|---|---|
|`Subject`|**这是谁的事实？**|真实被观察对象身份，自由标签：`reference:auto_skill_gen`、`implementation:target-product-eval`；单系统项目 `self`|
|`Channel`|这个事实从哪里观察到|`source` / `runtime` / `test` / `docs` / `stakeholder` / `data-snapshot`|
|`Reality`|这条事实描述现实的**哪一面**|`declared` / `implemented` / `reachable` / `executable` / `experienced`|
|`Kind`|它描述什么类型的现实|`interaction` / `presentation` / `intent`；**其余事实留空**（真实迁移测试：103 条 E-\* 中 `structure` / `behavior` 使用数为 0 且无 Gate / 下游消费者，已从枚举删除——Kind 只服务真实 consumer，不做分类劳动）|
|`Locator`|在哪里找到|文件/symbol/route/会话/截图路径；**不得指向 `.engineering/work/` 或 `/tmp`**（见 §9）|
|`Observation`|实际观察到什么|只写该证据能直接支持的内容|
|`Boundary`|有效范围|Collection / Search Boundary + Status|

### Subject 只表示身份
`Subject` 回答「谁」，不回答「关于什么」。意图、历史、目标都是**事实的性质**，用 `Kind` / `Reality` 表达：

```text
✅ Subject: implementation:xxx   Kind: intent   Channel: stakeholder   Reality: declared
   Observation: 产品同事称最终应支持图片生成
❌ Subject: intended / historical / target / legacy        ← 禁止
```

多 Subject 项目（replication / migration / 对照）里，**同一功能的两侧必须各成一条 Evidence**；跨 Subject 的 Claim 必须显式写「A 侧… / B 侧…」，禁止把两个系统合并成一条「现状」。

### Reality 是 facet，不是成熟度等级
**禁止把五值实现成 ordinal**，禁止任何「系统最高已经到哪一级」的推导。一条 Evidence 尽量只描述一个 facet；多个 facet 由不同 Evidence 分别记录，由 Claim 综合：

```text
E-101  Subject: impl  Reality: implemented  Channel: source   Observation: image_gen adapter 存在
E-102  Subject: impl  Reality: experienced  Channel: runtime  Observation: 当前用户流程没有生图入口
C-xxx  Claim: Capability implemented but not available in the observed user experience.
```

「UI 暴露了一个 disabled 功能」= `experienced` 成立而 `executable` 不成立，两者并存合法。

### 最小证据适配规则（取代 authority matrix）
```text
experienced → direct runtime / UI observation（Validator 机械检查：Channel 仅接受 runtime）
executable  → runtime execution / test / direct trace（Validator 机械检查：Channel 仅接受 runtime / test / data-snapshot）
reachable   → runtime 或完整 reachability evidence
implemented → source / test
declared    → docs / config / explicit statement
```

Evidence 的 `Reality` 值若没有对应 Channel 的支持，就**不得声明该值**；其中 `experienced` / `executable` 有上述机械检查，其余 facet 的合法组合较宽，由 Claim 综合与语义判断把关（不要据此扩大 Validator 职责）。这不构成等级：`source` 证据可以很强地证明 `implemented`，但它永远给不出 `experienced`。

Evidence 本身不等于结论。

**Stakeholder statement 是 Evidence，不是自动事实**：只用于回答 source / runtime 永远回答不了的高价值 Unknown（产品目的、哪些是 placeholder、哪些明确没接完、reference 与 demo 冲突时哪个更接近目标）。记录时必须写清 **who said what / 它 resolve 哪个 Question / 是否与 runtime 或 source 冲突**；冲突时按 §8 并列记录，不得单方面覆盖。`Channel: stakeholder`、`Kind: intent`，**不建 Stakeholder Registry**。

**Runtime Experience Evidence（截图 / DOM / walkthrough / 录屏）**：Agent 直接查看，按同一 schema 记录——`Channel: runtime`、`Reality: experienced`、`Kind: interaction | presentation`、`Locator` 指向**可长期重放**的路径、`Observation` 只写该证据中**实际可见**的事实。不需要 screenshot registry，也不新增 evidence 类型。

边界：单张截图不能证明完整 interaction sequence，只能证明该时刻的可见状态；截图未显示的内容不得脑补；跨状态结论需要按 Job 顺序采集的多份证据支撑。

## 3. Claim Type
- `OBSERVED`：Evidence 中直接可见的事实，例如「按钮触发 endpoint X」「函数写入文件 Y」。
- `DERIVED`：由一组 OBSERVED 事实直接推导，例如「保存后立即持久化」。
- `INFERRED`：合理解释/设计意图/未直接验证的行为，例如「该结构可能意味着 Draft 不是核心概念」。

禁止把静态源码的 DERIVED/INFERRED 结论写成 runtime OBSERVED。

**OBSERVED 的观察对象必须与 Claim 主语一致**：读 `App.tsx` 看到 10 个 route，OBSERVED 的是「代码里有 10 个视图定义」，不是「用户能看到 10 个入口」；读 `onClick` 看到绑定 `POST /run`，OBSERVED 的是「代码声明了这个绑定」，不是「用户点击后真的发生了什么」。**关于用户实际经历（看到什么、从哪里开始、做完后界面如何变化、什么最显眼）的 Claim，只有 runtime / 截图 / walkthrough 直接观察到该界面状态时才是 `OBSERVED`；从源码结构推出的只能是 `DERIVED`。**

## 4. Confidence
独立于 Claim Type：

- `已确认`：直接证据或充分交叉证据支持。
- `高概率`：多条一致线索，无直接确认或仍存在有限边界。
- `未确认`：合理但证据不足。

## 5. Claim Strength × Evidence Authority
核心规则：**Claim 的强度不得超过 Evidence Authority 实际能证明的范围。**

特别约束：

- 静态 source 不能自动表述成 runtime 已观察事实；
- runtime observation 只证明实际观察到的环境和路径；
- test 只证明对应测试范围；
- `唯一 / 不存在 / 始终 / 从不 / 所有` 等强结论必须有明确 Search Boundary 和足够覆盖，否则降级为弱 Claim 或记为 Unknown。

不增加「P0 必须 runtime」这类绝对规则，只要求强度与 Authority 相称。

Authority 匹配（证据是否足够取决于 Claim）：

- runtime 行为优先 runtime/test；
- 实现路径优先 source/symbol；
- 当前可达性需要 route/entry/runtime；
- 负面结论需要 bounded exhaustive search；
- 设计意图通常只能写 INFERRED，除非有权威文档明确说明。
- **Reality facet 与 Channel 的适配关系以 §2「最小证据适配规则」为唯一权威**（五值 facet 非等级，不在此重述）。不存在固定「源码永远高于 UI」的总排序，也不存在 facet 之间的单调升级路径。
- **用户可观察体验**——默认状态是工作态还是管理态、第一次从哪里开始、Primary CTA 与可见 affordance、主要 interaction primitive、操作后的可见反馈、loading / error / disabled 表现、信息与视觉层级、完成与失败信号——属于 `Reality: experienced`，**只能由 runtime 观察支持**；source 与 docs 对这类结论最多给到 `implemented` / `reachable`，写 Claim 时对应 `DERIVED`，不是 `OBSERVED`。

**执行环境缺少某条证据通道时**（无 runtime / 无 test 执行 / 无 shell）：对应 Claim 按可用 Authority 封顶，并如实记录缺失——不得制造该通道的结论，也不得因为某通道缺失而降低其他通道的标准。

**没有 Baseline 不等于证据不足**：Baseline 是已有知识的组织方式，不是证据质量的必要条件。直接观察 Repo / Runtime / 测试 / 数据快照，仍然可以形成高可信 Evidence；可信度取决于实际观察范围、来源通道、可重放性与是否直接支持结论。新鲜的 runtime 观察可以比旧 Baseline 更可信；记录“无 Baseline、本次观察范围是 X”是诚实边界，不是自动降级。

**Fidelity 场景额外约束**：会被下游当作 Target Fidelity Requirement 的 UX Claim，若没有 `Reality: experienced` 的 Evidence 支持，`Confidence` 不得高于「高概率」，并必须同时留下 Unknown（「未做 runtime 观察」）。不得仅凭 `Replication Impact` 有值就自动升级为保真契约。

## 6. Search Boundary
任何 `唯一/全部/没有/不可/不会` Claim 必须记录 Search Boundary 与 Boundary Status：

- `EXHAUSTIVE_WITHIN_SCOPE`
- `PARTIAL`
- `UNKNOWN`

Boundary 必须拆两栏，二者不一致时以 executed 为准：

- `declared`：声明的检查范围（例如「web/src 全量」）。
- `executed`：**实际执行的检索**——工具 + pattern / 查询式 + 范围 + 执行日期。

缺 `executed` 的负面结论不得写 `EXHAUSTIVE_WITHIN_SCOPE`，只能记 `UNKNOWN`。原因：按命名约定猜检索式是最常见的假阴性来源——真实实现可能是顶层导出、字符串字面量或另一套命名，与约定不匹配就查不到，而 declared 栏看起来仍然「全量」。executed 栏的作用是让负面结论可被重放。

`PARTIAL/UNKNOWN` 时不能把「未发现」提升为系统级不存在。

### 修表述 ≠ 否定结论
`EXHAUSTIVE_WITHIN_SCOPE` 缺 executed 记录时，说明的是**这条表述超出当时证据能力**，不是「结论全部未知」。两种合法处置任选，禁止第三种（为清零而批量改写成 UNKNOWN）：

1. **补 executed**：实际重做那次检索并记录工具 + pattern + 范围 + 日期；命中若与结论冲突，按 §8 并列记录。
2. **降表述**：Boundary Status 改为 `PARTIAL`，**结论原文保留**，并注明「表述降级、未否定」。

选择依据是影响面：真正影响 P0/P1 Product Reality 或下游设计决策的负面/枚举 Claim 值得补证；低影响历史结论降级即可。补证时警惕**检索式陷阱**——按命名约定猜的检索式（如 `api.evaluate`）会漏掉真实实现（如 `streamSse('/api/evaluate')` URL 字面量），产生假阴性；一次只按一种检索式得到的「未发现」不足以支撑 exhaustive。

### declared ≠ executed（可达性与能力声明）
对用户可观察行为，证据必须跨过「声明」到达**至少一个实际执行路径**（例如 UI control → handler → runtime call，或 route → loader → provider）。具体怎么追——call graph / string search / route map / wrapper search / runtime probe——由模型按目标仓的代码结构决定，本 Skill 不固化 technique。

不得从 config / docs / 注册表 / 模块清单直接推出「运行时真的可达」或「已接线」。这类只能记为 declared；需要 executed 证据才能升级为可观察事实。declared 与 executed 之间的差距本身就是要登记的 Unknown，不能用「文档里写了」填平。

## 7. Unknown Registry
Unknown 至少包含：`U-ID / Question / Impact / Supporting Evidence / Contradicting Evidence / Required Authority / Status / Resolution Claim`。

状态：`OPEN / INVESTIGATING / BLOCKED / RESOLVED`。只有满足 Required Authority 的新 Evidence/Claim 才允许 `RESOLVED`。

## 8. Contradiction
冲突先并列记录，不静默调和。写明：Claim A/Evidence / Claim B/Evidence / 影响 / 需要的额外 Authority / Resolution Status。

**Intent 与 Implementation 冲突是常态，两者都要保留**：半成品 Demo 里「注释/文档/stakeholder 说要做 A」与「现状做了 B」同时成立是合法结论，不得为了 Product Model 自洽而把历史意图改写成现状，也不得把意图当作现状能力。写法：Intent 记 `INFERRED/PROBABLE` + 来源，Current 记实际观察到的那一个，缺口进 Unknown。

**Source 与 Runtime 冲突时**（源码看起来支持 A，runtime 实际表现 B）：对**用户可观察体验**，Current-State = B；Source 只用于解释「为什么代码最终表现成这样」，不得用 source 推断覆盖 runtime 观察。若 runtime 表现可能受环境 / feature flag / 账号状态影响，记录 `OBSERVED runtime state + environment boundary + Unknown whether universal`，不擅自推广为全局结论。

## 9. Canonical Evidence vs 临时产物 vs 当前可见投影
产物边界：

- **canonical Evidence**：`evidence/` 下的 `E-*`（含 `packets/`），可以完整保存；
- **临时产物**（探索比较、browser dump、中间截图、草稿）：放 `.engineering/work/`，不是 canonical，**不得作为任何结论的唯一正式证据来源**。

Product Model、Task Map、Behavior、Coverage 只能引用 canonical Evidence。

### 归并前证据强度自检（语义判断，不机械化）
对所有描述**用户动作、可见状态、交互行为**的 Claim，以及任何「已接线 / 可运行 / 用户可用 / AVAILABLE / WIRED」类断言：确认至少有一条能**直接观察或证明该行为**的 UI / runtime / execution-path 证据。API、backend、config、docs、注册表、模块清单只能证明「支撑机制存在」或「能力被声明」。

- 缺执行证据时的合法结论是 **`仅声明（declared only）`** 或 **`未接线`**——不得写成「已执行 / 用户可用」。
- 反向同样合法：**「文档声明了能力，但当前实现未接线」本身是重要调查结论**，应如实登记，不因缺执行证据而视为不合格。
- 本条是归并前 self-check，不做 keyword 分类、不按前端路径命名猜测、不新增 Claim/Evidence taxonomy。

Canonical Evidence 可以完整保存；当前调查只加载回答 Question 所需的 Evidence/Claim 摘要和必要原文。压缩 model-visible context 不等于删除 Evidence。

### Locator 必须可重放
被 canonical 结论引用的证据文件**不得放在 `.engineering/work/` 或 `/tmp`**——`.engineering/work` 的定义是可丢弃，`/tmp` 会随环境重启消失。规则：

- `Locator` 指向 workspace 内的**非 `.engineering/work` canonical 位置**：文本类事实指向代码/文档路径；截图等证据文件直接放在其所属 canonical 目录（baseline 侧为 `product/evidence/`，module 侧为 `modules/<module-id>/verification/`），**不为此新建子目录或 subsystem**；
- 证据已不可获得（如已删除的 `/tmp` 截图）时，该行降级为 `证据不可重放 / NOT VERIFIED`，**禁止猜、禁止改写为通过**。

## 10. Interaction 与 Presentation 是 primitive reality
两者都是**已经真实失败过**的不可约维度，用 `Kind` 表达，不新建 ID namespace：

**`Kind: interaction`** —— 过程中界面如何实际变化：user action / previous state / next state / visible mutation / available next action / blocking-waiting / completion-failure / persistence。

> **只记录会改变用户可观察体验的状态转换**，不保存所有内部 reducer / event。

例：`提交 → message append → running step 出现 → tool activity inline → partial output append → evaluation 出现 → final result`。这是 Product Experience reality，不是实现细节。

**`Kind: presentation`** —— screen skeleton / primary workspace / secondary region / component morphology / information grouping / hierarchy / density / disclosure / state placement。

理由：`diagnostic cards` 与 `management table` 可能有相同 behavior capability，但**不是同一个体验**；`conversation progressive stream` 与 `modal wizard + result page` 可以承载完全相同的 Journey。Presentation 不是 polish，属于可观察 Product Reality。

### 但 Presentation 不能膨胀成视觉数据库
不保存：每个像素、全部 spacing、全部 RGB、全部 DOM、全部 CSS rule。
只保存：**「如果删掉它，会不会让两个本质不同的体验塌成同一个表示？」**（区分能力测试）

> 这是 **Semantic Losslessness，不是 Implementation Losslessness**。

### Interaction ≠ Journey
`Journey` = 用户为什么来、完成什么任务、从 Start 到 Success（derived view）。
`Interaction` = 过程中界面如何实际变化（primitive）。
相同 Journey 可以拥有完全不同的 Interaction，所以 Journey 摘要**不能替代** interaction Evidence；反之亦然。

## 11. 能力边界（信息论层面，不是 workflow 指令）
> **本 Skill 重建的是产品语义、行为与体验事实，不提供实现层无损编码。**
> **Baseline 是 Product Reality model，不是 Source Replacement。**

`Source → Semantic Model → Regenerated Source` 存在天然信息损失：真实项目的核心 Route 可达上万行，体验由组件结构、状态、事件顺序、时序、样式、mock runtime、异常态、响应式、局部条件共同决定，而这些不可能全部进入语义模型。因此当目标要求**源码级高保真复刻**且原始源码可获得时，直接保留/迁移源码天然比「先逆向抽象、再重新生成实现」具有更高的 implementation fidelity。

由此：

- 完成标准是「当前知识是否足以支持用户要求的下一步（**理解、诊断、设计、复刻或重构**）」，**不是**「是否保存了足够信息让另一个 Agent 无源码重写等价系统」；
- Replication / fidelity 场景可以要求更高的 Interaction / Presentation 覆盖，但**仍不宣称无损实现重建**；
- Replica-Ready 的实现规格（`spec/`）目标是让未参与调查的 Coding Agent 独立开发功能与行为高度相似的新系统，**不是**无损源码重建；规格可承载开发级语义，但每个重要结论必须可追溯到 `E-*` / `C-*` / `J-*` / `B-*`；
- 影响重建正确性的代码机制（接口、数据、状态、权限、校验、副作用、异常、后台/集成）必须作为 canonical `E-*` 证据记录；`intelligence/` 缓存仅用于导航，不作为产品事实权威（见 §1 与 `code/intelligence-contract.md`）；
- 禁止通过继续增加字段、规则、Registry、Agent 来追求「无损复刻」——那是用错误目标消耗工具本身。
