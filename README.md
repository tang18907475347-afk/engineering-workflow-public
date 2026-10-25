# Product Engineering

一个统一的产品工程 Plugin：把「按需理解产品现状 → 明确目标与设计 → 工程实施 → 独立验证与纠错」放在同一套可信知识上，并在合并前独立处理云端 Agent 的 AI 评审发现，同时允许简单工程任务完全不依赖全量产品逆向、Clarification 或 Handoff。

它不是更大的工作流，也不是知识治理系统。它只统一三件事：

1. **知识落在哪里、谁维护**（`workspace-and-ownership.md`）；
2. **事实如何被证据修正、旧结论如何失效**（`evidence-and-correction.md`）；
3. **设计决定如何进入工程、交付状态与验证证据如何解释**（`delivery-and-handoff.md`）。

**第一次使用？** 先看 [用户提示词教程](USER_PROMPTS.md)，里面有按能力划分的可复制提示词和授权边界。

## 关于这份副本

这是从内部实践版本整理出来的**脱敏副本**：文档、契约与判断规则完整保留，与特定公司环境绑定的部分已经拆掉。

**已移除（不随本副本提供）**

| 原能力 | 状态 | 自己补什么 |
|---|---|---|
| 缺陷平台客户端 | 移除 | `bugfix` 的采集 / 分析校验 / 回写入口，按各 reference 的参数语义实现 |
| MR 评审评论后端 | 改为占位 | `skills/ai-code-review/scripts/mr_backend.py` 的 `run_tool()`，契约在该文件头部 |
| 需求文档采集 | 移除 | `product-design` 的文档采集入口，落位契约见 `references/clarification/acquisition.md` |
| 内部打包/发布配置 | 移除 | 按 `scripts/package-plugin.py` 的清单格式接自己的分发通道 |

**仍然开箱可用**：`product-engineering` 路由、`product-reality` / `product-design` / `implementation-strategy` / `test-readiness-review` 的全部契约与校验脚本、`ai-code-review` 的离线确定性工具（artifact / patch / check-envelope / HTML 决策页）、`skill-architecture`、Figma 采集（MCP 或 `FIGMA_TOKEN`）、结构校验与打包脚本。

**前置条件**：Python 3.9+（仅标准库）；可选 PyYAML（更严格的 frontmatter 解析）、ffmpeg（视频证据抽帧）、playwright-cli（`ai-code-review/tests/ui_behavior_check.sh`）。

外部依赖只有公开标准：GitLab REST / GitHub API、Figma REST 与 Dev Mode MCP、unpkg CDN。

## Skills

| Skill                     | 作用                                                                                                   | 主要落位                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `product-engineering`     | Router：按用户真实动作选择一个能力；不自动串行推进                                                     | 只读 `.engineering/`                                                                      |
| `product-reality`         | 理解代码机制、产品行为、用户路径与证据边界；轻量问题直接回答，Baseline / Spec 由 Scope、Rigor 与持续消费价值决定 | `.engineering/product/`、`.engineering/intelligence/`                                     |
| `product-design`          | 需求理解、产品语义澄清、目标体验设计；纯按确定设计稿实现默认由 Coding Agent 承担                       | `.engineering/requirements/<req>/clarification/`、`.engineering/design/`、`modules/<id>/` |
| `implementation-strategy` | 把目标与 Current Repo 结合，产出可执行的 Requirement Workspace                                         | `.engineering/requirements/<req>/workspace/`                                              |
| `test-readiness-review`   | 独立判断交付是否达到 `READY_FOR_TEST`，给出证据边界                                                    | 只读，不持久化报告                                                                        |
| `ai-code-review`          | 先验证 MR 上的 AI 评审意见并产出 review.json + 本地 HTML 决策页；人工决策后只执行授权项，平台反馈独立处理；支持多轮复审 | `.engineering/work/ai-review/`；scratch，不写入 canonical；反馈写回 MR                    |
| `bugfix`                  | 缺陷单据的采集、分析、修复、回写（平台客户端不随副本提供，见下节）                                     | `.engineering/issues/`                                                               |
| `skill-architecture`      | 判断已有 Skill / Plugin 的真实架构、责任分配与变更尺度；独立能力，不接入 Router                        | 独立诊断；不依赖 `.engineering/` 工作区                                                   |

Router 只负责选择与交接。典型路径是：

```text
（按需）Product Reality
        ↓
（按需）Product Design
        ↓
Implementation Strategy → Coding → Test Readiness Review → QA

独立通道：AI Code Review（合并前评审问题）、缺陷闭环（bugfix）
```

这不是强制流水线，Product Reality 也不是必经阶段。简单任务可以直接实现；用户已提供充分、可信的现状时可直接进入设计或实施；没有 Baseline、Clarification 或 Handoff 时，直接从原始来源开始。Product Reality 的 Scope（单链路/模块/域/系统）与 Rigor（证据与行为恢复程度）是两个独立维度，交付由目的决定；Replica-Ready 可应用于任何 Scope，不默认全产品逆向，也不默认最小调查。局部诊断可以是有界调查，复刻或结构性重构则必须覆盖目标范围内的关键与边缘路径。

### 为什么是六个业务 Skill

不是按历史工作类型划分，而是按稳定的问题类型：

| 能力                      | 回答的问题                     |
| ------------------------- | ------------------------------ |
| `product-reality`         | 现在是什么                     |
| `product-design`          | 应该是什么                     |
| `implementation-strategy` | 怎么改                         |
| `test-readiness-review`   | 改得对不对                     |
| `ai-code-review`          | 外部评审意见是否成立、怎么处理 |
| `bugfix`             | 外部缺陷如何闭环               |

代码机制调查不单独占一个 Skill：它是 `product-reality` 的一种持久化形态，与 `product/` 引用同一段源码但服务不同消费者，不要求统一 schema。

AI 评审问题也不单独建设知识体系：它直接消费 MR、Diff、Repo 与可选的上游上下文，复用 MR 平台后端的评论 CRUD，不维护第二套 issue 状态；判断与证据随对话 / MR 回复交付。

`test-readiness-review` 保持独立，不是因为“独立 Skill 天然保证上下文隔离”，而是因为当前 IS / TRR 边界清晰、没有实质重复或路由冲突，合并收益不足、改造风险更高。它的裁决权威来自契约，不来自目录名称。

### 独立能力（不接入 Router）

| Skill                | 作用                                                   | 说明                                                                            |
| -------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `skill-architecture` | 判断已有 Skill / Plugin 的真实架构、责任分配与变更尺度 | 独立诊断能力，不接入 Router，也不参与产品工程链路；放在插件内只为统一管理与部署 |

`skill-architecture` 直接读取被审对象，不依赖 `.engineering/` 工作区，也不依赖本插件的其他 Skill；其 `references/` 按原仓库结构保留。需要时直接点名使用，Router 不会自动路由到它。

并入时按文件拷贝，保留 `SKILL.md`、`README.md` 与 `references/`，未保留其独立仓库历史；更新时从该能力的独立来源同步，不在本插件内维护第二套内容。

## Workspace

```text
<project-root>/.engineering/
├── PROJECT.md
├── product/                       # Current Reality
├── requirements/<req>/
│   ├── sources/
│   ├── clarification/
│   └── workspace/
├── design/                        # Desired Reality
│   └── module-handoffs/<module-id>/<handoff-id>.md
├── modules/<module-id>/
├── intelligence/
├── issues/
└── work/                          # 可丢弃 scratch
```

- 单根 `.engineering/`；项目根 `.gitignore` 统一忽略。
- 不是每个任务都创建全部目录；按需创建最小结构。
- `PROJECT.md` 只做导航，不拥有状态。
- `product/` 是 canonical 产品证据；`intelligence/` 是可丢弃的代码机制缓存。两者可以引用同一段源码，不要求统一 schema，也不要求只保留一份。

## Shared contracts

三份契约是 Authoring SSOT，运行时由 `scripts/sync_shared_references.py` 确定性复制到依赖它们的 Skill 的 `references/`：

| Contract                            | 解决的问题                                                                  |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `shared/workspace-and-ownership.md` | 单根工作区、canonical ownership、引用与最小恢复                             |
| `shared/evidence-and-correction.md` | 证据与修正边界、product/ 的 E/C 记录、相关性失效、“无 Baseline ≠ 证据不足” |
| `shared/delivery-and-handoff.md`    | 决定状态与 Basis、Binding / Adjustable、不可变 Handoff、状态轴、TRR 四问    |

### Decision status 与 Basis

```text
Status: PROPOSED | ACCEPTED | SUPERSEDED
Basis:  DECISION | EVIDENCE | DERIVATION | DESIGN_JUDGMENT
```

`DERIVED` 不是 Status。一个推导结论本身仍可能是 Proposed / Accepted / Superseded。只有以下内容能进入工程 Binding：

- 用户/授权人明确接受的决定；
- 由已接受约束**严格必要**推出的内容；
- 由接受决定直接定义的 Preserve / Verification Obligation。

设计模型自己的“合理推导”默认是 `PROPOSED` / Adjustable，不能自动制造产品要求。

### Handoff

- 只有存在真实下游消费者、且需要版本追溯时才发布不可变快照。
- 路径：`design/module-handoffs/<module-id>/<handoff-id>.md`；内容不可变，`Status` / `Superseded-By` 可变。
- 简单 UI 修改、同一上下文连续完成的设计+实现，不需要 snapshot、ID 或 supersede 链。
- 消费者记录精确 `handoff-id`；失效检查只看当前交付依赖的决定、Preserve、Verification Obligations 和相关证据。新发现的、未被引用的关键事实也可以触发检查。

### Verification

TRR 对每个 Expected 回答：`Expected → Evidence Required → Evidence Available → Proven`。

`PASS — CODE / DOM / INTERACTION / VISUAL / NOT VERIFIED` 是证据描述，不是验收要求，也不映射为 TRR 状态。设计侧的 `PASS` 可以作为 Evidence Available 输入，TRR 独立判断它是否覆盖当前 Expected。

### AI Code Review

- 云端 AI 评审意见是待验证的发现，不是技术事实或必须执行的命令。
- 严重性标签与处理决策分离：高严重性可以是误报，低严重性也可能值得修。
- 修前只写 `CONFIRMED / DISMISSED / NEEDS_EVIDENCE`；`FIXED` 是执行并验证后的结果，不是修前 verdict。
- 先产出 `review.json` 与本地 `review.html` 决策页；人只做一次修复决策，Coding Agent 只执行校验为 `AUTHORIZED` 的项。
- 模型用字段 patch 批量更新 `review.json` 的 analysis；脚本重算 `proposalFingerprint`、校验并原子写入，不手改大 JSON。
- 互不依赖的 finding 可并行分析；并行 worker 只产出 patch fragment，合并后一次写入。
- 平台 `closed=1` 的评论默认只进入 `closedFindings` 汇报，不分析、不决策；需要重审时显式 `--include-closed`。
- 决策用稳定 `reviewKey` + Finding 级 `proposalFingerprint` 关联；方案、根因或证据变化的 Finding 单独 stale，不整份失效。缺失或过期指纹不授权。
- 问题风险 `issueRisk` 与修复风险 `proposal.fixRisk` 分开；问题严重不等于修复代价高。
- 目标 artifact 已有 analysis 时默认拒绝覆盖；用 `--out` 保留旧分析，只有显式 `--force` 才丢弃。
- 不建 `decisions.json` 强制文件；Decision Envelope 在复制时生成，平台反馈是决策/执行后的独立动作。
- 平台状态（`pending / handled`）与代码是否正确分离；`closed=1 / adopted=0` 是已关闭但未采纳，不等于已修复。
- `headMatches=false`、`branchMatchesSource=false`、`dirty=null` 都是预检信号，不是唯一准入；执行前必须核对代码锚点和证据是否仍适用。
- HTML 对评论、diff 和代码做安全转义；LocalStorage 不可用时用导出/导入或剪贴板兜底。
- 不依赖 PRD / Workspace；只有 finding 成立依赖产品意图时，才按需读取上游上下文。

## 使用

```text
继续推进这个需求，先定位已有产品事实、设计决定和工程计划。
基于当前产品现实设计目标体验；明确哪些决定已接受，哪些仍是提案。
把这个需求落成可执行计划，并说明上游知识是否仍然有效。
检查当前交付是否达到 READY_FOR_TEST，给出证据与未证明范围。
处理这个 MR 上的 AI 评审意见：先分析并生成 review.html，等我决策后再执行。
处理这张缺陷单。
```

更完整的提示词模板、常见坏例子和授权边界见 [USER_PROMPTS.md](USER_PROMPTS.md)。

## 维护与验证

```bash
# 结构校验（Skill 名称、资源引用、manifest、shared copy drift）
python3 scripts/check_plugin.py

# 共享契约同步（改 shared/ 后必跑）
python3 scripts/sync_shared_references.py

# 结构回归（validator、生成副本与打包产物）
python3 scripts/test_regressions.py

# 产品设计采集脚本测试（需要 pytest）
python3 -m pytest skills/product-design/tests -q

# AI Code Review 脚本测试（unittest，不访问外部服务）
python3 -m unittest discover -s skills/ai-code-review/tests -v

# 打包插件
python3 scripts/package-plugin.py --target all    # 两个都打
python3 scripts/package-plugin.py --target qoder  # 只打 Qoder → dist/qoder/
python3 scripts/package-plugin.py --target codex  # 只打 Codex → dist/codex/
```

`package-plugin.py` 是唯一打包入口，`--target` 默认 `all`。Qoder 包使用 `.qoder-plugin/plugin.json`，Codex 包使用 `.codex-plugin/plugin.json`；两者都只带各自清单和共享 `skills/`，不会混入对方 manifest。`--output` 只用于单目标包。

`check_baseline.py` 只做 Current Reality 的结构校验，不证明语义收口：

```bash
python3 skills/product-reality/scripts/check_baseline.py <project>/.engineering/product
```

## 设计原则

- **统一知识的消费与修正，不统一模型的判断过程。**
- **明确事实与决定的权威，不把 Skill 变成权威本身。**
- Owner 是 canonical 维护责任，不是语义权威；决定的有效性取决于 `Status` / `Authority` / `Basis`。
- 跨能力复用是机会，不是准入条件；没有上游知识就直接查原始来源。
- 只修正受影响的理解；不建 Registry、不做自动传播、不要求全量重算。
- 不把所有产品体验缺口自动升级为当前 Requirement 的 P0 Blocker。
