<!-- Generated from shared/glossary.md by scripts/sync_shared_references.py. Do not edit this copy directly. -->
# 术语速查
> **这张表只做白话翻译，不定义规则。** 每个术语的正式含义以括号里注明的契约为准；两边说法不一致时，以契约为准，并修正本表。
> 用法：看到不熟悉的词时按名字查；最后一节列出最容易搞混的几组词。

## 1. 决定与权威（delivery-and-handoff.md）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|`D-*` / Decision-ID|一条产品或设计决定的编号|设计、澄清、计划里记录“定了什么”|验收项 `AC-n` 的“来源”常写 `D-n`|
|`PROPOSED`|提案：还没人拍板|模型自己提出的方案默认都是它|模型觉得“明显该这样”也还是 PROPOSED|
|`ACCEPTED`|已确认：用户或授权人明确拍板了|用户说“确认 / 就这么定”之后|必须写清是谁（Authority）、哪天（Accepted-At）|
|`SUPERSEDED`|已被新决定替换，只留作历史|决定改了的时候|不删除，写上被谁替换（Superseded-By）|
|Status|这个决定现在处于哪一步|每条决定都要写|和 Basis 是两回事：Status 回答“定了没有”|
|Basis|这个决定是凭什么来的|`ACCEPTED` 时必填|取值：用户拍板（DECISION）、证据（EVIDENCE）、推导（DERIVATION）、设计判断（DESIGN_JUDGMENT）|
|Authority|谁有权、谁确认了这个决定|`ACCEPTED` 时必填|用户、产品负责人、设计负责人等|
|严格必要推导（Strict Derivation）|从已确认决定里“不这样就不成立”地推出来的内容|`Basis: DERIVATION` 时|自问：去掉这条推论，那个已确认的决定还能成立吗？能成立 → 它只是建议，标 PROPOSED。例：确认了“详情用抽屉”，不等于确认了“支持深链、返回时恢复滚动位置”|
|Binding|下游**必须遵守**的部分|消费设计交接、写计划、提测审查|只有：已确认的决定、它的严格必要推导、由已确认决定直接定义的 Preserve 与验证义务|
|Adjustable|下游**可以调整**的部分|同上|PROPOSED 的设计提案、开放问题；不能伪装成 Binding|
|Preserve|改动后**不能被破坏**的现有行为或约束|设计交接、计划、提测审查|计划里的 `P-n` 就是 Preserve|
|Verification Obligation|必须证明的事（只说证明什么，不规定怎么测）|设计交接、提测审查|例：“两个字段同时违规时都要标红”必须有交互层证据|
|Handoff（模块交接）|设计交给工程的一份**不可变快照**|只有存在真实下游消费者、且需要知道“工程当时消费的是哪个设计版本”时才发|路径 `design/module-handoffs/<module-id>/<handoff-id>.md`；正文写后不改，只改 Status|
|Handoff 的 READY / BLOCKED / SUPERSEDED|交接可用 / 有具体卡点不可用 / 已被新版本替换|消费交接时先看|BLOCKED 必须写出具体卡点|

## 2. 证据与现状（evidence-and-correction.md、product-reality）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|Current Reality / Desired Reality|系统**现在**是什么 / 目标**应该**是什么|区分现状与设计|现状不自动成为约束；设计也不能写成现状|
|`E-*`（Evidence）|一条可重放的观察记录|深度模式下写 `product/` 证据|八列：编号、对象、通道、面、种类、定位、观察、边界|
|`C-*`（Claim）|对一组证据的解释或结论|深度模式|结论强度不能超过证据范围|
|`J-*` / `B-*`|用户任务（Job）/ 行为契约（Behavior）的派生视图|深度模式、复刻规格|它们从证据推出来，不是新事实|
|五个面：declared / implemented / reachable / executable / experienced|资料声明了 / 代码实现了 / 用户能走到 / 实际能跑通 / 用户实际体验到|判断“这个功能到底有没有”|**五个面，不是五个等级**，不能互相推导：代码里有 ≠ 用户能走到|
|Channel|证据从哪个通道来|写证据时|源码（source）、运行时（runtime）、测试（test）、数据快照、文档等|
|Boundary / Search Boundary|这次观察或搜索覆盖到哪里|写结论、尤其是“没有”类结论时|“在 src/order 下没找到删除入口”，不能写成“没有删除入口”|
|OBSERVED / DERIVED / INFERRED|直接观察到 / 由观察推出来 / 推测|标结论的可信度|推测不能悄悄升级成观察|
|DIAGNOSED / VALIDATED|设计侧：已诊断 / 已验证|设计记录|和上一行是两套词，不能互相冒充|
|Unknown（Unknown Registry）|明确登记的“还不知道”|深度模式收口前|高影响的 Unknown 没解决，不能宣称收口|
|canonical|正式的、权威的那一份|判断该读哪里、该改哪里|与之相对的是 scratch（`.engineering/work/`，可随时删，不能被正式结论引用）|
|derived view（派生视图）|从正式产物里挑出来、重新组织给某个读者看的视图|`reality.md`、`spec/`|只引用，不另立事实|

## 3. 现状调查的范围与完成标准（product-reality、deep-mode.md）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|Scope|这次调查的范围|深度模式开始时|单链路 / 模块 / 业务域 / 完整系统；不默认全产品|
|Rigor|这次调查要做到多严|深度模式|和 Scope 独立：小范围也可以要求很严|
|Baseline|一次完整的现状调查成果（`product/`）|系统级理解、复刻、重构|它是调查结论，不是每个任务的前置条件|
|Baseline Status：IN_PROGRESS / PARTIAL / COMPLETE / BLOCKED|进行中 / 有可靠结论但有缺口 / 已诚实收口 / 缺的条件现在拿不到|Baseline 的总状态|COMPLETE 表示调查诚实收口，**不表示产品完整**|
|Baseline Scope / Spec Target Scope|调查覆盖的范围 / 需要能被重建的范围|复刻|调查范围可以比复刻范围大，两者不能互相替代|
|Replica-Ready|规格已经足够让一个没参与调查的开发者独立重建|复刻任务|由规格是否充分和阻塞缺口决定，不由文档数量或校验通过决定|
|Design Readiness|现状理解已经足够支撑设计|Baseline 收口时|判据见 coverage-and-readiness.md 第 7 节|
|Inventory|调查范围内的“分母”：页面、接口、后台任务、文档等清单|深度模式开头|先列全，再逐项处置|
|COVERED / EXEMPT / OPEN|已覆盖 / 有据排除 / 尚未处置|Coverage 表|EXEMPT 的理由必须相对于当前范围；OPEN 收口前要清零或转成 Unknown|
|intelligence（代码机制缓存）|只记“查起来贵”的代码事实的缓存|跨文件调用链、分支差异、坑|可以整目录删掉重建；没记 ≠ 不存在|
|cache miss / stale hit|缓存里没有（回源码查就好）/ 缓存里有但已经过时或错了|用缓存时|stale hit 最危险：宁可没记，不可记错|
|locator|能让人重新找到证据的定位|写任何事实时|优先 `文件#符号`，其次源码里能直接搜到的字面量；不用行号|
|reality.md（需求级现状摘要）|为一个需求整理的现状派生视图|设计找痛点、计划定 Preserve、提测做回归|写现状，不写方案；“这是现状，不是期望”|
|`PC-n`|reality.md 里“候选的不能破坏的行为”|计划确认 Preserve 时|确认之后才成为计划里的 `P-n`|

## 4. 设计判断（product-design）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|问题定义|业务定位 + 带证据的痛点 + 聚焦 + 根因|设计目标体验之前|出方案前默认请用户确认|
|HARD 约束|设计必须满足的硬条件|设计推导时|法规、对外协议、兼容性、业务铁律、用户明确的长期要求；逐条写依据|
|PHASE 约束|只影响“分几步做到”，不否决设计本身|排交付路径时|“这期时间不够”是 PHASE，不能拿来否决理想结构|
|ROOT FIX / MITIGATION / LOCAL IMPROVEMENT|修到根因 / 只减轻症状 / 与根因无关的局部改善|描述改动性质|说清当前改动属于哪一种|
|surface / reach|一个界面面 / 问题或改动影响到的范围|判断根因归属|本 surface、共享资产（SHARED_SURFACE）、还是系统级|
|SHARED_SURFACE|根因在多个界面共用的组件、token 或外壳里|判断根因归属|同一种问题在多处各自出现，**不等于**共享根因|
|materially different（真正不同的方案）|在对象组织、生命周期、旅程结构、能力分组、模块边界或交互模型上不同|决定要不要给备选方案|只是导航位置、配色、文案不同，不算两个方案|
|PASS — CODE / DOM / INTERACTION / VISUAL / NOT VERIFIED|这次实际验证到了哪一层|设计侧实现后|每一层只证明它自己那件事；是证据描述，不是验收结论|

## 5. 计划、执行与提测（implementation-strategy、test-readiness-review）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|Requirement Workspace|一个需求的工程计划目录（`requirements/<req>/workspace/`）|写计划、执行、提测审查|`plan.md` 是入口|
|「给执行者」|`plan.md` 开头的执行规则|写代码时|在哪里停、怎么记录、不擅自提交|
|「验收与保持」/ `AC-n` / `P-n`|执行者、提测审查、bugfix 共用的期望清单：验收项 / 不能被破坏的现有行为|计划、执行、提测、缺陷分析|每个任务写明覆盖哪些编号；`check_plan.py` 检查覆盖关系|
|`T-n`|计划里的一个任务|计划与执行|任务以 `T-n` 开头|
|Delivery Liabilities|交付前必须清理的临时东西|计划收尾|mock、调试入口、临时开关、测试数据|
|提测条件就绪 / DONE / delivery-ready|实施侧自检的三个程度：可以提测 / 需求实现与约定验证完成 / 临时代码也已清理|实施计划收尾|都是实施侧自己的判断，**不等于** READY_FOR_TEST|
|TRR（test-readiness-review）|独立的提测审查|代码写完准备提测时|最好在新会话或子代理里运行|
|Expected Contract|TRR 本次审查用的期望清单|TRR 第 1 步|有「验收与保持」时从它出发，并独立核对|
|READY_FOR_TEST / BLOCK|TRR 的两种结论：可以交给 QA / 有阻塞项|TRR 结束时|BLOCK 后回原实现会话修，再在新会话复审|
|审查记录（reviews/）|每次 TRR 留下的一份结论记录|复审、交 QA、bugfix 引用|写后不改；它是“某次审查的结论”，不是当前事实|
|fresh context|不继承实现过程对话的新上下文|TRR|保证审查独立|

## 6. AI 评审处理（ai-code-review）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|finding|云端 AI 留的一条评审意见|处理 MR 评论|是待验证的发现，不是事实|
|assessment：CONFIRMED / DISMISSED / NEEDS_EVIDENCE|修前结论：成立 / 不成立 / 已查到仓库知识的边界，需要外部信息|修前分析|`FIXED` 不是修前结论，是执行后的结果|
|recommendation：FIX / DEFER / DISMISS / NEEDS_EVIDENCE|推荐怎么处理|修前分析|严重性不决定处理方式|
|issueRisk / fixRisk|问题本身的风险 / 按方案修复的风险|修前分析|两者分开判断：问题严重不等于修起来代价高|
|APPROVE / CLOSE / DEFER / PROVIDE_INFO / UNDECIDED|人在 HTML 里的决定：批准修复 / 关闭评论（不改代码）/ 暂不处理 / 退回重评 / 尚未决定|人工决策|只有 APPROVE 和 CLOSE 构成执行授权|
|AUTHORIZED / STALE / INVALID|`check-envelope` 的校验结果：可以执行 / 方案已变需重新决策 / 无效不执行|执行前|STALE 只停这一条|
|reviewKey / proposalFingerprint|评审身份（`仓库#MR id`）/ 某条意见当前分析方案的指纹|授权匹配|方案变了指纹就变，旧授权自动失效|
|Decision Envelope|人在 HTML 里决策后生成、交给执行者的授权包|执行阶段|不需要维护 decisions.json|
|adopt / ignore / reject|平台上的反馈动作|决策和执行之后，单独确认|不会从 APPROVE / CLOSE 自动推导|
|closedFindings|平台上已关闭的评论，只汇报不分析|生成 review.json 时|需要重分析时用 `--state all`|

## 7. 缺陷闭环（bugfix）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|四条通道：采集 / 分析 / 修复 / 回写|拉单 / 写分析档案 / 改代码 / 改单据状态与评论|处理缺陷|互相独立，用户点到哪条做哪条，做完即停|
|档案（dossier）|一条缺陷的分析结果文件|分析与修复之间|格式是机器读取的接口，保持稳定|
|完成度：完成 / 暂定 / 待人工证据 / 暂定·用户接受进修复|分析结论有多可靠|档案头部|用户接受暂定结论，不等于证据已经完成|
|档位：全自动 / 半自动 / 手动|这个修复 Agent 能自己完成到什么程度|修复前|只表示自动化程度，**不授予** commit 或回写权限|
|my-bugs / pending / archive|待分诊 / 已分析待拍板 / 已归档|采集后的三份清单|每次拉取重新派生，唯一的持久状态是 analyses/ 目录|
|需求口径|这条缺陷对应的有效期望|写档案时|优先引用需求的 `AC-n` / `P-n`；没有时用 PRD|

## 8. 工作区与上下文（workspace-and-ownership.md）
|术语|白话|什么时候会用到|例子 / 容易混淆的地方|
|---|---|---|---|
|`.engineering/`|所有插件产物的根目录|任何读写|默认被 .gitignore 忽略|
|`PROJECT.md`|导航页：去哪里找|开工时|只做导航，不存状态|
|`context.md`|跨需求的业务上下文与纠偏记录|每个 skill 开工时|用户的纠正当场写入；模型的推断不写入|
|owner（区域维护者）|负责某个 `.engineering/` 区域保持可读、可修正的 skill|判断该改哪里|**不是**语义权威；决定是否有效看 Status / Authority|

## 9. 最容易搞混的几组
- **两种“owner”**：工作区里的 owner 是“哪个 skill 负责维护这块产物”；代码缓存里的 owner 是“这条事实写在哪个源码文件的哪个符号里”。
- **一堆“完成”**：Baseline `COMPLETE`（调查诚实收口）≠ Handoff `READY`（设计可供消费）≠ 计划 `DONE`（实施侧自检完成）≠ `READY_FOR_TEST`（独立审查通过）≠ `PASS — INTERACTION`（某一层验证通过）。它们回答不同的问题，不能互相推导。
- **Status 和 Basis**：Status 回答“定了没有”，Basis 回答“凭什么”。
- **Preserve 的三个样子**：`reality.md` 的 `PC-n`（候选）→ 计划确认后成为 `P-n` → TRR 逐条核对。
- **ai-code-review 的三套词**：修前结论（CONFIRMED…）、人工决定（APPROVE…）、平台动作（adopt…）彼此独立，不能互相映射。
- **现状和期望**：`reality.md`、`product/` 写的是现状；`AC-n`、已确认决定写的是期望。现状不自动成为约束，现有实现也不自动成为产品期望。
