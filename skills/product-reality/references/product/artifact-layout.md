# Artifact Layout

**适用范围**：本文件只描述决定持久化完整 `product/` 现实时的产物结构。它不是调查深度阶梯；轻量回答、`intelligence/` 缓存或一次性结论不要求创建这些文件。按知识性质与消费者选择产物形态，按需创建最小结构。

## 推荐目录
工作区根与跨 Skill canonical 归属见 skill-local `references/workspace-and-ownership.md`；本文件只定义 Current Reality（`product/`）内部结构，落盘于 `<project-root>/.engineering/product/`。

```text
.engineering/product/
├── BASELINE_INDEX.md
├── product-model/
│   ├── INDEX.md
│   └── <domain>.md
├── task-map/
│   ├── INDEX.md
│   └── <domain-or-job-family>.md
├── behavior/
│   ├── INDEX.md
│   ├── cross-cutting.md
│   └── <domain>.md
├── evidence/
│   ├── INDEX.md
│   ├── questions.md
│   ├── claims.md
│   ├── unknowns.md
│   ├── contradictions.md
│   └── packets/
├── coverage/
│   ├── INDEX.md
│   ├── surfaces.md
│   ├── objects.md
│   ├── journeys.md
│   ├── handoffs.md
│   └── gate.md
└── spec/
    ├── INDEX.md
    └── <scope>.md
```

## 分层与产物职责
**`evidence/` 是唯一存放 primitive fact（`E-*`）的地方**；`product-model/`、`task-map/`、`behavior/`、`coverage/`、`spec/` 是 derived view（synthesis / projection），引用 `E-*` / `C-*` / `J-*` / `B-*` ID，不复制长证据。被 view 压缩掉的事实必须仍能在 `E-*` 中找到——Interaction 与 Presentation 尤其容易被 Journey 摘要吃掉，它们必须是 primitive。

`spec/` 是实现规格（Replica-Ready 交付物），可承载完整开发级语义（Behavior Contracts、接口、数据、状态机、权限、校验、副作用、异常、acceptance），但每个重要结论必须可追溯到 canonical `E-*` / `C-*` / `J-*` / `B-*`；Evidence 变化后必须重新核对并更新受影响节，不声称自动重生。`spec/INDEX.md` 签发 **Spec Target Scope**（独立 Coding Agent 需要重建的范围）、与 **Baseline Scope** 的关系、Dependencies & Boundaries、以及 **Replica-Ready Judgment 的唯一当前判断**（是/否 + blockers 引用 Unknown Registry）。`BASELINE_INDEX.md` 只引用，不重复签发。单链路/模块级 Replica-Ready 可以直接产出 `spec/`，不强制初始化全套 Baseline 产物；新建 spec 使用 `assets/spec.template.md`，小 Scope 单文件、大 Scope 可拆分。

各产物职责：

|产物|放什么|不放什么|
|---|---|---|
|`BASELINE_INDEX`|版本身份、范围、进度、P0/P1、当前 Question、高影响 Unknown、Gate|长调查正文|
|`product-model`|领域、Surface、对象、状态所有权、依赖|User Journey 长叙述|
|`task-map`|L1 Jobs、Journeys、Job Dependencies、优先级|API/源码审计细节|
|`behavior`|可观察状态语义、门禁、恢复、副作用|页面目录|
|`evidence`|Questions/Evidence/Claims/Unknowns/Contradictions/Trace|无证据的最终 ontology|
|`coverage`|Inventory Coverage Ledger（分母来自 Inventory，逐项 COVERED/EXEMPT/OPEN + 理由）、Closure Matrix、Search Boundary（declared/executed）、Gate|长篇产品解释|

## 分片规则
按稳定领域/对象生命周期/可独立追踪 vertical slice 分片，禁止按任意文件大小或每页面/每 endpoint 分片。

满足任一条件时创建 shard：多个 P0/P1 Job 或明显不同 Journey / Evidence 跨多个服务且 INDEX 已难读 / 可按独立问题单独调查 / Behavior 密度高导致跨域语义被淹没。

小系统不要强制分片。

## Index 纪律
目录有多个 shard 时必须有 `INDEX.md`：范围 / shard 状态 / 关键 ID / cross-links / 未解决高影响项。

`evidence/` 下的内容（含 `packets/`）是 canonical Evidence；临时调查产物放 `.engineering/work/`，不是 canonical。Product Model / Task Map / Behavior / Coverage 只能引用 canonical `E-*`，不能把临时文件作为唯一正式证据来源。
