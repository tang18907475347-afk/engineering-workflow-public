# Workspace 表达参考
Workspace 承载当前工程指导，不规定判断过程。落在项目 `.engineering/requirements/<requirement-slug>/workspace/`；路径用 repo-relative，不写本机绝对路径。

## 文件选择
- `plan.md`：Workspace 的恢复与实施入口。背景、目标、当前机制、工程落点、风险和验证按任务组织，不固定章节数、编号或顺序，不适用的内容直接省略。
- `anchors.md`：可选来源与代码 / API / test 导航。入口少时内联于 plan，不维护文件清单或第二份需求。
- `phase-NN-<slug>.md`：真实依赖、独立交付、协作冲突或验证边界值得拆分时使用；不根据模块数或行数自动拆分。
- `brief.md`：只在有不读 Workspace 的实际读者需要时生成，生命周期见下。
- 原始 PRD、设计与附件仍在同需求 `../sources/`，澄清在 `../clarification/`，不复制成另一套来源。

## 内容与导航
已确认且影响执行的产品信息重组为工程输入。具体 payload、分类与内容种子、默认值、固定文案、关联关系、事件参数不能只留一个类型定义或“见 PRD”。上游未确定的事实保留未知。

来源链接可用于追溯、核验与补缺；执行者发现指导与来源或 Repo 冲突时可按需读取，不能静默改变已接受目标。代码定位优先文件 + 符号，不依赖易腐烂的持久行号。

Task 是有独立接手价值的工程闭环，不是每个文件一个任务。读者应能恢复该任务的目标、必要上下文、推荐修改、依赖与完成条件；共享上下文可引用同一 Workspace 小节，不必逐任务复制。Phase 同样只承载实际边界，不为每个 Phase 添加 Gate。

验证应说明验证什么、如何执行和必要条件；需要外部账号、数据、环境或联调时写出实际缺口。已有 PASS 记录是可用证据，不自动构成当前计划的验证义务或完成裁决。提测条件就绪、DONE、delivery-ready 的含义见 SKILL.md；独立 READY_FOR_TEST / BLOCK 由 test-readiness-review 另行判断。

## 当前真相与修订
plan 描述现在怎么实现、当前推进位置、未决项与完成条件。现实推翻旧 claim 时原地改写，删除 stale task / evidence，不在旧方案后追加“更正”形成双轨。留下后续执行者能够按此维护的简短说明；默认被忽略的 Workspace 不保证旧版本恢复，只有纳入 Git 的内容才能依赖版本历史。

可保留仍能避免重复误判的 Decision Notes。Delivery Liabilities 只记录真实存在、交付前需要退出的临时实现及退出条件，不记过程流水账。

## 一次性人读 brief
落在 `.engineering/requirements/<slug>/brief.md`。标明生成时点、基线 commit、实际 canonical 来源路径及“过期以 Workspace 为准”。按真实读者组织内容，不固定视角或版式；允许为独立阅读内联必要上下文。

brief 不进入后续 reconciliation、不反向成为 Workspace 权威；需要新版时重新生成，不增量同步。项目已有分发目录时可同次复制，不建设新 Reference / Gate / Validator。
