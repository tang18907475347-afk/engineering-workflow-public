# 0.10.0 变更说明

本版是在 0.9.0 基础上的**局部改进**：结构、Skill 名称、契约语义都不变。每一项都对应讨论中确认的一个决定（D1–D13），可以单独验证、单独回退。

## 两条底线
1. 每个 Skill 都能独立运行：上游产物只加速，不是前提，每个消费点都写明退路。
2. 不受模型强弱限制：目标与质量标准只写要达到什么；接口与工具只规定格式；方法辅助一律“默认做法 + 可以不用”。

## 逐项说明

| # | 决定 | 改了哪些文件 | 回退方法 |
|---|---|---|---|
| D1 / D10b | product-reality 入口先分流；深度模式的原文**逐字**移到 `deep-mode.md`，核心不变量保持原编号（5–11 留在 SKILL.md，1–4、12、13 移入 deep-mode.md） | `product-reality/SKILL.md`、`references/product/deep-mode.md`（新）、`references/product/investigation-questions.md`（一处指向） | 用 0.9.0 的 SKILL.md 覆盖，删除 deep-mode.md，恢复那一处指向 |
| D2 | 新增需求级现状摘要 `requirements/<req>/reality.md`（派生视图，只引用定位）；候选 Preserve 编号 `PC-n` | `product-reality/SKILL.md`「轻量 B」、`assets/reality.template.md`（新）、共享契约第 1、3 节；design / IS / TRR 的读取说明 | 删除「轻量 B」一节与模板，撤回各处读取说明 |
| D3 | product-design 以“问题定义”为默认起点；出方案前默认确认；打分与根因分类作为可选的默认做法；正反例用于校准 | `product-design/SKILL.md`、`references/design/problem-definition.md`（新）、`references/design/examples.md`（新）、`assets/design.template.md` | 删除 SKILL.md 中「先定义问题，再设计方案」一节与两个新文件 |
| D4 | Workspace `plan.md` 固定「验收与保持」（`AC-n` / `P-n`），任务注明覆盖；TRR 从清单出发并独立核对；bugfix 需求口径引用 AC；覆盖检查脚本 | `implementation-strategy/SKILL.md`、`references/workspace-format.md`、`scripts/check_plan.py`（新）、`tests/test_check_plan.py`（新）；`test-readiness-review/SKILL.md`；`bugfix/references/analyze.md`；`ai-code-review` 的 SKILL.md、`triage.md`、`verification.md` 各一处 | 撤回固定章节说明；脚本可单独删除（几次需求下来从未拦到问题时，按约定删除） |
| D5 | TRR 每次审查写一份写后不改的审查记录 `requirements/<req>/reviews/` | `test-readiness-review/SKILL.md`「审查记录」、共享契约第 1、3 节 | 删除「审查记录」一节，恢复“禁止创建持久化 Review 报告” |
| D6 | 两条底线写入 README「设计原则」 | `README.md` | —— |
| D7 | 新增 `.engineering/context.md`：业务上下文与纠偏记录，准入与修正规则只在共享契约第 9 节定义一处；bugfix 与 ai-code-review 也同步该契约 | `shared/workspace-and-ownership.md` 第 9 节；各 Skill 的读取说明；`scripts/sync_shared_references.py` | 删除第 9 节与各处读取说明；撤回同步依赖 |
| D8 | `plan.md` 开头固定「给执行者」，执行规则跟着产物走 | `implementation-strategy/references/workspace-format.md`、`SKILL.md`；router 的“直接实现”一行 | 删除该固定块的说明 |
| D9 | Router 只读进度脚本 | `product-engineering/scripts/req_status.py`（新）、`tests/test_req_status.py`（新）、`SKILL.md` | 删除脚本与 SKILL.md 中那一段 |
| D10a | ai-code-review SKILL.md 按 format-compression 流程评估 | **未改动**：可压的只有约 60 字节空行与 37 字节表格 padding；逐句比对与 reference 的原文重复约 3%；14 条“禁止”属于受保护的硬门禁。按该流程“收益很小 → 保留原样” | —— |
| D11 | 决定记录字段按需必填（ACCEPTED 时必填 Authority / Accepted-At / Basis；DERIVATION 时必填 Derived-From + 严格必要理由），语义与 Binding 规则不变 | `shared/delivery-and-handoff.md` 第 1 节、`product-design/SKILL.md`、`assets/design.template.md` | 恢复原字段块与表格列 |
| D12 | 现有方法类内容保持原写法，只在有失败证据处加默认起点（目前只有 D3） | 无 | —— |
| D13 | skill-architecture 补“模型相对性”：**只起草，不改本插件内的副本**（该能力从独立来源同步） | `docs/proposals/skill-architecture-model-relativity.md`（新） | —— |
| D14 | 术语速查：每个术语一句白话、何时用到、例子与易混点；文件头声明“以契约为准”，不新增定义 | `shared/glossary.md`（新）及 7 个 skill 的生成副本、各 SKILL.md 的 reference 索引一行、README 一行、同步脚本 | 删除该文件与索引行，撤回同步依赖 |

## 已经验证的（静态）
- `scripts/check_plugin.py` 结构校验通过；共享契约副本与源一致。
- 全部原有测试通过（结构回归、check_baseline、ai-code-review 82 项、product-design 采集脚本）；新增 `check_plan.py` 8 项、`req_status.py` 5 项测试通过。
- D1 的搬移经逐行比对：0.9.0 SKILL.md 的每一行都能在新 SKILL.md 或 deep-mode.md 中原样找到，例外只有 description（加了 reality.md 触发词）、两个标题名、代码问题收口那一句的前缀。

## 还需要实测的（行为）
静态检查只能证明“没有丢失文本、没有破坏已知消费者”，不能证明模型行为变好。建议用 2–3 个做过的真实需求：

1. **弱模型（你主力的 flash 模型）**：分别用 0.9.0 与 0.10.0 跑 design → 计划 → 提测审查。看三件事：你需要纠正几次；问题定义里的重点痛点是否与你当时的判断一致；下游需要回头重问上游的次数。
2. **强模型（你能用到的最强模型）**：同样的需求，看默认做法有没有拖慢它、产出质量有没有下降（例如是否机械地套用打分表）。
3. 某一项没有效果或起反作用，按上表单独回退。
