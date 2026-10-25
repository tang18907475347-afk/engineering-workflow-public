# Workspace and Ownership
本契约定义项目知识的落位与维护责任，不授予额外产品决策或写入权限。

## 1. 单根工作区
所有持久化知识落在项目根的一个目录：

```text
<project-root>/.engineering/
├── PROJECT.md
├── product/                       # Current Reality：当前系统事实、证据、当前解释
├── requirements/<req>/
│   ├── sources/                   # PRD、设计稿、附件（唯一来源资产）
│   ├── clarification/             # 需求 × 交互澄清
│   └── workspace/                 # 工程实施计划、锚点、交付记录
├── design/                        # Desired Reality：目标体验与已接受设计决定
│   ├── module-handoffs/<module-id>/<handoff-id>.md
│   └── ...
├── modules/<module-id>/           # 单个模块的设计、实现记录与验证证据
├── intelligence/                  # 高成本代码事实缓存（按需）
├── issues/                   # 缺陷档案（独立通道）
└── work/                          # 可丢弃 scratch；不得被 canonical 结论引用
```

不是每个任务都需要全部目录。Skill 启动时先发现 `.engineering/`：存在则按各自入口恢复；不存在则按需创建当前任务真正需要的最小结构。不为路由或“制度完整”预建空目录。

项目根 `.gitignore` 统一忽略 `.engineering/`。是否把 canonical 产物纳入版本控制由项目决定；`work/` 是可丢弃 scratch，不纳入版本控制。

## 2. Experience Project Root 与 Subject Sources
- **Experience Project Root**：`.engineering/` 所在根，可以等于业务源码仓，也可以独立。
- **Subject Sources**：被观察/修改的一个或多个源码、运行时或外部系统。

源码仓可写且用户希望就地维护时，两者通常相同。以下情况 `.engineering/` 必须落在 Experience Project Root，不强行写入 Subject Source Root：只读 checkout、vendor / 第三方源码、外部 snapshot、一个项目含多个 source roots、用户不希望污染源码仓。

`PROJECT.md` 记录 `Experience Project Root` 与 `Subject Sources`。不引入 multi-repo manager；多源码仓只是多个 subject 路径。

## 3. Ownership 的含义
**Owner = canonical 维护责任，不是语义权威。**

- Owner 负责让该区域的内容可读、可核验、可修正，并在受影响时做一次一致性检查。
- Owner 不因为“写了文件”而获得替用户做产品决定、替证据下结论或替其他 Skill 审批的权力。
- 一个决定是否有效，取决于它的 `Status`、`Authority` 与 `Basis`（见 `delivery-and-handoff.md`），不取决于它写在哪个 Skill 的目录。
- 其他 Skill 可以读取、引用、摘要任何 canonical 区域；写入与修正按第 5 节执行。

|区域|Canonical 维护者|主要消费者|主要内容|
|---|---|---|---|
|`product/`|product-reality|product-design / IS / TRR / Coding Agent|当前事实、证据、Claim、任务地图、覆盖边界、Implementation Spec（derived）|
|`intelligence/`|product-reality|任意工程 Skill|高成本代码事实缓存；可整目录删除重建|
|`requirements/<req>/sources/`|product-design|product-design / IS|PRD、设计稿、附件与来源清单|
|`requirements/<req>/clarification/`|product-design|IS / TRR / product-design|需求理解、关键风险、待确认、已记录决定|
|`requirements/<req>/workspace/`|implementation-strategy|Coding / TRR|实施计划、锚点、决策记录、交付证据|
|`design/`|product-design|IS / TRR / 实现|目标体验、设计决定、模块 handoff|
|`modules/<module-id>/`|product-design（设计侧）/ 实现任务（验证侧）|后续任务|模块级设计、实现记录、验证证据|
|`issues/`|bugfix|缺陷闭环|缺陷档案、分析、修复记录|
|`work/`|当前任务|无|scratch，可丢弃|

“设计侧”与“验证侧”同处一个模块目录时，按文件头或小节标明来源；不要用目录位置制造新的审批关卡。

## 4. 引用而不是复制
- 跨 Skill 引用优先给稳定 ID（`E-*` / `C-*` / `J-*` / `B-*`）或路径 + 小节锚点，不重抄长证据。
- 下游可以为执行方便写局部摘要；摘要必须足够当前任务使用，并标明来源。**不得维护另一份与 canonical 冲突的权威。**
- 上游知识不存在、不可信或与当前源码冲突时，直接从原始来源（PRD、设计稿、Runtime、源码）开始，并标注实际观察范围；不要因为“没有 Baseline / 没有 Handoff”而拒绝完成简单任务。
- `intelligence/` 与 `product/` 可以引用同一段源码：前者是代码机制缓存，后者是产品证据。来源重叠不等于知识重复，不强制统一 schema，也不要求只保留一份。
- 引用失效是线索，不是唯一失效信号：新发现的、此前未被引用的关键事实也可能影响当前交付。消费者负责在发现时记录并按 `evidence-and-correction.md` 修正。

## 5. 写入与修正
- 新事实：在当前任务的 canonical 区记录实际观察、来源与边界。`E-*` / `C-*` 是 `product/` 的记录格式；其他区域可用持久路径引用证据，不强制注册 ID。
- 局部修正：当前 Skill 对**直接受影响**的 Claim / View / 设计记录就地修正，保留 Revision 与修正依据。
- 跨域重新综合：当影响跨多个 Claim / 领域时，标 `Impact Review`，由区域 owner 做一次语义综合；不是自动传播，也不是全库重写。
- 未决冲突：写入 `PROJECT.md` 的 Open Issues / Conflicts，不静默选边。
- ID：`E-*` / `C-*` 在同一 `product/` 内唯一；跨区域引用带路径，不引入全局 allocator / registry。

写入规则不扩大用户授权；只读审查不因发现事实错误而变成自动改写任务。

事实与决定的修正边界见 `evidence-and-correction.md`；决定状态与 handoff 见 `delivery-and-handoff.md`。

## 6. PROJECT.md 只做导航
`PROJECT.md` 是项目级恢复入口，不是第二套状态机。它只记录：

- Experience Project Root / Subject Sources；
- 当前有哪些 canonical 区域与入口文件；
- 当前进行中的需求 / 模块（如有）；
- 未决冲突与需要人决定的问题（指针，不复制全文）；
- 最近一次已知的全局变化（可选）。

不要求固定 frontmatter，不要求每次任务都更新。Skill 自己的 INDEX / 计划回答“进去后从哪里继续”，`PROJECT.md` 只回答“去哪里找”。

## 7. 恢复与最小读取
1. 从当前工作目录向上找最近的 `.engineering/`；找不到时，以当前 Git worktree 根为候选项目根。
2. 读 `PROJECT.md`（若存在）与当前任务相关的 1–2 个入口文件。
3. 进入被选中的 Skill 后，按该 Skill 自己的 INDEX / 计划恢复；只读当前任务直接相关的上游引用。
4. 不默认重扫整个 repo、重读整个 Baseline / Design，或把所有 `.engineering/` 文件灌入上下文。需要更多信息时再扩大读取范围。

## 8. 最小结构
新项目第一次写入时，只创建：

```text
.engineering/
├── PROJECT.md
└── <当前任务需要的区域>/
```

其余目录在真实需要时创建。不要为了“统一”复制一套空模板。
