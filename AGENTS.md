# 维护本插件之前必读

本文件写给接手维护这个仓库的任何 Agent（以及人）。它记录的是**怎么改**这个插件，不是插件怎么用（用法见 [README.md](README.md) 与 [USER_PROMPTS.md](USER_PROMPTS.md)）。改动之前先读完本文件。

## 1. 第一原则：改动尺度跟着根因走
- **先确认根因，再选尺度。** 根因在单点就单点修正；只有根因确实在模型、边界或知识架构时，才考虑合并、拆分或重建。改动大小本身既不是优点也不是缺点。
- **用户的使用反馈是最重要的行为证据。** 用户说“大问题没有，细节需要完善”，就意味着局部修正，而不是重构。
- **真实教训**：曾有一次重构在没有确认根因的情况下就选择了“大改”——按生命周期阶段拆成 9 个 skill、全部改名、删掉 Baseline / Replica-Ready 体系与决定语义、把判断写成强制步骤。它违反了本仓库自己的 skill-architecture 原则，丢失了低频但高价值的能力，最终被整体回退。不要重复这条路。

## 2. 两条底线（任何改动都要逐条核对）
1. **每个 Skill 都能独立运行。** 上游产物只用来加速，不是前提。每个读取上游产物的地方都要写明“有就用；没有就回到原始来源（PRD、代码、diff），并在产出中说明缺了什么、按什么处理”。
2. **不受模型强弱限制：弱模型能被提升，强模型不被束缚。** 新增内容按三类写：
   - **目标与质量标准**：只写要达到什么，不写怎么做；
   - **接口、状态与工具**：只规定格式，尽量由脚本检查；
   - **方法辅助**：一律写成“默认这样做；你有能达到同样质量的做法时可以不用，说明即可”。
   只有授权（commit、push、回写、外部反馈）与机器消费的格式写成必须遵守。

另外：每个改动都应能单独回退；行为效果要在一个弱模型和一个强模型上实测后才能宣称“已提升”。

## 3. 改动流程
1. **先读**：README、本文件、`docs/CHANGES-*.md`（已决定事项与理由）。审视任何改动时，以 [skills/skill-architecture/](skills/skill-architecture/SKILL.md) 为标准：先重建实际行为面，再判断责任分配，最后才决定改多少。
2. **提建议，不直接改**：每个议题写清问题、证据强度（可裁决 / 很可能需确认 / 需要行为验证）、建议、备选方案、代价、回退方式。一次一个议题。
3. **由用户决定**：用户拍板之后才实施；决定记录进当前版本的 `docs/CHANGES-<version>.md`。
4. **实施**：局部改动；改 `shared/` 后运行同步脚本；新增或改变术语、契约语义时，同步更新 `shared/glossary.md`（术语速查只做白话翻译，以契约为准）；跑完第 6 节的全部检查。
5. **如实汇报**：静态检查通过只能说明“没丢文本、没破坏已知消费者”，不能说明模型行为变好；没实测就写“未实测”。

## 4. 受保护的内容（未经用户明确决定，不改语义）
- **Skill 的名称与边界**：现有 9 个 skill（`scripts/test_regressions.py` 会检查这个集合）。
- **三份共享契约的语义**（`shared/`）：决定状态与 Basis、Binding / Adjustable、证据的五个面（声明 / 实现 / 可达 / 可执行 / 体验）、工作区归属、业务上下文的准入规则。表达可以改进，语义不改；不要换成另一套词汇。
- **机器或下游消费的格式**：bugfix 的档案格式、卡片协议与三文档状态机；ai-code-review 的 `review.json`、Decision Envelope、`proposalFingerprint`；`check_baseline.py` 校验的 product/ 结构；`plan.md` 的「给执行者」与「验收与保持」；`reality.md` 与 `context.md` 的结构。
- **深度模式的规则**（`skills/product-reality/references/product/deep-mode.md` 及其引用的 reference）：使用频率低，但重要且复杂，不用 skill 单靠提示词很难做好、做标准。
- **硬门禁、停止条件、授权边界、反例与真实失败经验**：它们大多来自真实事故。
- **`skills/skill-architecture/` 的内容**：从独立来源同步，不在本仓库内修改；需要改时先在独立来源修改（修改提案放在 `docs/proposals/`）。

## 5. 不要做的事（都被认真考虑过，或真实发生过）
- 按生命周期阶段、作用范围（系统 / 模块 / 页面）或变化幅度拆分 skill。
- 把知识型 reference（诊断维度、防坑规则、判断标准）统一改写成强制步骤。只在有真实失败证据的地方加“默认做法”（0.10 的决定 D12）。
- 把打分公式、固定数量上限、全字段必填模板写进常驻正文，用来替代判断。
- 没有真实消费者就新增 registry、状态文件、校验器或流程关卡。
- 因为“使用频率低”删除高价值能力。
- 以“压缩”为名改写规则；压缩只按 `skills/skill-architecture/references/format-compression.md` 的流程进行，受保护内容不压。
- 未经用户要求就 commit、push，或改动 `main` 之外的分支策略。

## 6. 每次改动后必须通过的检查
```bash
python3 scripts/sync_shared_references.py      # 改了 shared/ 之后
python3 scripts/check_plugin.py --strict
python3 scripts/test_regressions.py
python3 -m unittest discover -s skills/ai-code-review/tests
python3 -m unittest discover -s skills/implementation-strategy/tests
python3 -m unittest discover -s skills/product-engineering/tests
python3 -m pytest skills/product-design/tests -q  # 需要 pytest
```

## 7. 已决定的事项
详见 [docs/CHANGES-0.10.md](docs/CHANGES-0.10.md)（D1–D14）与 [docs/CHANGES-0.11.md](docs/CHANGES-0.11.md)（D16–D17），每一项的理由、改动文件与回退方法都在里面。摘要：

| # | 决定 |
|---|---|
| D1 / D10b | product-reality 入口先分流；深度模式规则原文移入 `deep-mode.md`，一条不删 |
| D2 | 需求级现状摘要 `reality.md`：派生视图，只引用定位，供设计、计划、提测使用 |
| D3 | product-design 以“问题定义”为默认起点；出方案前默认请用户确认 |
| D4 | `plan.md` 固定「验收与保持」，执行者、TRR、bugfix 共用；`check_plan.py` 检查覆盖 |
| D5 | TRR 每次审查留一份写后不改的记录 |
| D6 | 两条底线（本文件第 2 节） |
| D7 | `.engineering/context.md`：业务上下文与纠偏记录；用户的纠正当场记录，模型推断不写入 |
| D8 | `plan.md` 开头固定「给执行者」，执行规则跟着产物走，不新增执行 skill |
| D9 | Router 只读进度脚本 `req_status.py`，不维护状态 |
| D10a | ai-code-review SKILL.md 按压缩流程评估后不改（可压收益很小，主体是受保护规则） |
| D11 | 决定记录字段按需必填，语义与 Binding 规则不变 |
| D12 | 现有方法类内容保持原写法，有失败证据处才加默认起点 |
| D13 | skill-architecture 补“模型相对性”：只有提案，待在独立来源审阅 |
| D14 | 术语速查 `shared/glossary.md`：只做白话翻译，以契约为准；同步到 7 个业务 skill |
| D16 | `review.html` 视图层重做：只改视觉与导航，决策语义、Envelope、localStorage 键、测试依赖的选择器与文案不变；新增的交互只是导航与筛选，不是决策快捷方式 |
| D17 | 新增 `work-retrospective`：复盘用户的请求与实际工作，独立能力，不接入 Router，只在用户明确要求时使用，默认不写文件；会话记录由用户或其 agent 按统一事件格式提供，skill 不自带采集器 |
