---
name: ai-code-review
description: 处理 MR 上由云端 Agent 生成的 AI Code Review 意见：先逐条验证并产出 review.json 与本地 HTML 决策页，由人决定采纳、调整、跳过或暂缓，再让 Coding Agent 只执行已授权项；平台反馈独立处理。不用于自己发起代码评审、提测就绪裁决或缺陷单处理。
---

# AI Code Review

## Runtime Contract
- **Outcome**：每条在范围内的 AI 评审意见都有基于本地证据的修前判断、根因、推荐方案与验证要求；平台已关闭项只进入 `closedFindings` 汇报，不纳入修前判断；人在 HTML 中完成一次决策（批准修复 / 关闭评论 / 退回重评）；`APPROVE` 由 Coding Agent 执行并验证，`CLOSE` 只结束评论、不改代码；平台反馈按需单独处理。用户明确只要分析 / 文档时，Outcome 收敛为 `review.json` + `review.html`，不执行代码、不提交平台反馈。
- **Done**：`review.json` 分析完整并通过校验；`review.html` 已生成；平台已关闭项已在 `closedFindings` 只读汇报；用户已产出 Decision Envelope；已授权项完成修改与验证，异常项明确报告；需要平台反馈时已单独核对。若用户只要求分析，Done 是分析产物与结论，不要求执行或反馈。
- **Next consumer**：用户；被交接的 Coding Agent；需要时由 `test-readiness-review` 做独立提测判断；云端评审 Agent（通过 MR 评论继续质疑）。
- **Stop**：不在用户决策前改代码，不自动提交平台反馈，不默认做第二轮人工 Review，不自己发起 code review，不自动合并 / 批准 / 推送，不把外部反馈当成问题已关闭，不把平台写回当作所有任务的必达结果。

这个 Skill 承接的是**合并前的外部评审发现**，不是一个更大的代码审计流程。它复用 MR 平台后端的 MR 评论 CRUD，不新建工单系统、知识平面、本地状态机或第三份决策文件。

## 适用与分界
|用户目标 / 表达|是否走本 Skill|
|---|---|
|“处理这个 MR 上的 AI 评审意见”“逐条看云端评审说得对不对”“先出方案我来决定”“修完回复并复审”|是|
|“帮我自己 review 一下这段改动”|否：本地自查走基础 Coding Agent|
|“提测前检查”|否：走 `test-readiness-review`|
|“这个需求怎么实现”“设计一下目标体验”|否：走 `implementation-strategy` / `product-design`|
|“处理这张缺陷单”|否：走 `bugfix`|

与相邻能力的边界：
- **`test-readiness-review`**：判断 Requirement 是否达到 `READY_FOR_TEST`；本 Skill 只处理外部 AI 评审问题，不产出提测裁决。
- **`product-reality`**：可以按需消费 `.engineering/intelligence/` 的代码机制缓存或 `.engineering/product/` 的产品证据，但不建立 Baseline；简单事实直接读源码。
- **`implementation-strategy`**：不为评审意见生成 Requirement Workspace；修复需要跨模块方案、迁移或架构调整时，在分析中说明范围，是否执行由用户决定。
- **`product-design`**：不设计目标体验。finding 依赖产品意图时，按需读取已有的 `clarification/` / `design/` 或询问用户，不自行发明产品决定。
- **`bugfix`**：缺陷单据有自己的采集、档案与回写通道；MR 上的 AI 评论不走缺陷通道。
- **基础 Coding Agent**：本 Skill 负责修前分析与授权边界；实际代码修改可由当前 Agent 或交接给 Coding Agent 执行。

## 输入与最小前提
- **仓库 + MR**：`repo` 使用仓库路径（如 `acme/webapp`），`mergeRequestId` 使用**项目级 `id`**，不是列表里的 `iid`。缺 `repo` 时可从目标 worktree 的 `origin` 推断。
- **MR 平台后端可用**：`<平台身份查询>` 有身份，`<平台后端状态查询>` 已授权；失效时按宿主提供的平台通道重新授权，不绕过平台客户端直连。
- **本地代码**：优先在当前 MR 的 source branch / worktree 上核对。`headMatches=false` 是信号，不是自动拒绝：执行前必须核对 finding 的代码锚点、行为和证据是否仍适用，不能只比较 SHA。
- **可选上下文**：`.engineering/context.md`（业务上下文）、`.engineering/product/`、`.engineering/intelligence/`、`.engineering/requirements/<req>/clarification/`、`.engineering/requirements/<req>/workspace/plan.md` 的「验收与保持」（`AC-n` / `P-n`）、`.engineering/design/`。存在就按需读取；finding 是否成立依赖产品意图时，优先引用「验收与保持」里的编号；**没有 PRD、Clarification、Requirement Workspace 或 Handoff 不构成阻塞**。用户纠正了你对业务的理解时，按 `references/workspace-and-ownership.md` 第 9 节写入 `context.md` 的纠偏记录。
- **MR 状态**：已合并 / 已关闭的 MR 仍可只读分析，但平台可能不再接受反馈；先确认状态，再决定是否只做报告。

## Finding 不是事实
云端评审意见是**待验证的发现**，不是 `E-*`，不是技术事实，也不是必须执行的命令。它可能来自真实缺陷、误读上下文、过期代码、对项目约定的不了解，或只适用于其他场景。
- badge 里的严重性（如 `缺陷 · 高`）是云端的先验标签，不是本地结论。
- `outdated` 只是提示，不代表问题已经消失；必须在当前代码上重新确认。
- `suggestion.diff` 是建议，不是可直接套用的补丁；上下文变化后可能失效。
- 平台评论里的“建议”只说明云端认为应该怎样，不证明运行时真的会发生。
- 只有本地在源码、Diff、测试、运行时或数据快照中实际观察到的内容，才能作为判断依据。负向结论（“不会发生”）必须能说明检查边界。

## 判断模型
一条 finding 是否值得处理，取决于以下问题，而不是固定的检查清单：
|维度|要回答什么|
|---|---|
|Trigger|评论声称的触发条件在当前代码里真的可达吗？谁调用、什么输入、什么状态、有没有前置守卫？|
|Impact|一旦触发，坏在哪里：正确性、安全、数据、可用性、性能、可维护性还是纯风格？影响谁？|
|Probability|触发需要多罕见的输入 / 状态 / 时序？是常规路径还是理论边角？|
|Scope|是本 MR 引入的，还是既有问题？修它是否超出当前 MR 的交付边界？|
|Cost / Risk|修复改多大、触碰哪些 owner、需要什么验证？修复本身会不会引入更大风险？|
|Evidence|支撑上述判断的证据是什么？来源、范围、可重放性如何？|

### 严重性与处理决策分离
```text
云端严重性 = 缺陷 / 安全 / 性能 / 可维护性 / 风格 × 高 / 中 / 低
问题风险   = 影响面 × 触发概率 × 是否本 MR 引入
修复风险   = 契约影响 × 跨 owner 程度 × 可逆性 × 验证成本
处理决策   = 修复收益 vs 修复风险，以及当前 MR 的 scope
```
不要建立“高严重性 → 必须修”“低严重性 → 可以忽略”的映射。高严重性的误报应当用证据关闭；低严重性但真实、修复便宜且能防止回归的问题可以修。严重性是输入，决策是输出。

报告里分开写 `Issue Risk` 与 `Fix Risk`，各自取 `high / medium / low`。它们是决策依据，不是平台 badge，也不直接映射为某个动作。

### 本地风险分档

风险拆成两个维度，不能混用：

**问题风险 `issueRisk`**：问题本身一旦发生会造成什么。

|档位|判断锚点|
|---|---|
|`high`|安全 / 权限 / 数据损坏 / 可用性 / 资金等高风险；影响面广；触发概率高|
|`medium`|真实行为错误或回归，影响局部但路径可达|
|`low`|边角输入、局部可维护性 / 风格问题；影响小、易回退|

**修复风险 `fixRisk`**：按这个方案修，会带来什么代价。

|档位|判断锚点|
|---|---|
|`high`|改变公共契约、跨多个 owner、大范围迁移、难回退，或验证成本 / 不确定性很高|
|`medium`|局部 owner、范围可控，但需要明确回归验证|
|`low`|局部、低耦合、易回退，验证直接|

问题风险高不代表修复风险高；局部改动也不代表问题影响小。`issueRisk` 是判断辅助，不是自动公式；同一个 finding 在不同 MR scope 下可以不同。`analysis.issueRisk` 与 `proposal.fixRisk` 分别描述两件事，不要互相替代。

### 修前 assessment
|Assessment|含义|推荐动作|
|---|---|---|
|`CONFIRMED`|问题在当前代码中成立，触发与影响有证据|`FIX`（给方案与验证）或 `DEFER`|
|`DISMISSED`|问题不成立、不可触发、不适用或已被当前代码解决|`DISMISS`，给反证|
|`NEEDS_EVIDENCE`|现有证据不足以判断，需要云端或用户补充信息|`NEEDS_EVIDENCE`，列开放问题|

`FIXED` **不是修前 verdict**。只有代码修改并验证后，执行报告才能写 `IMPLEMENTED` / `FIXED`。`APPROVE / CLOSE / UNDECIDED` 是人工决策，不是 assessment；`ADOPT / REJECT / IGNORE / NONE` 是平台动作，三套语义分开。`UNDECIDED` 不是可选结果，只代表「尚无有效授权」（未处理或被 stale / invalid 降级）。

### 平台状态与本地判断分离
从 `list_merge_request_ai_comments` 观察到的状态；唯一映射源是 `platform_interpretation`（CLI / Artifact / HTML 都只消费它的结果，不各自解读 `adopted/closed`）：
```text
PENDING              ≈ adopted == 1 且 closed == 0
CLOSED_NOT_ADOPTED   ≈ closed == 1 且 adopted == 0   已关闭但未采纳
IGNORED              ≈ closed == 1 且 adopted == 3   已忽略（目标平台单 MR 观测）
CLOSED_WITH_ACTION   ≈ closed == 1 且 adopted 为其他/未观测值   已处理、动作未知
```
这只是**平台是否已经处理过这条评论**，不是“代码是否正确”。特别注意两点：
- `CLOSED_NOT_ADOPTED`（已关闭未采纳）不能当成已修复。
- `IGNORED`（已忽略）在平台上把“问题不成立（应为误报）”和“成立但暂不修（真正的 ignore）”合并进同一档，**从平台状态读不出技术结论**；也不能因为全部 IGNORED 就推断是批量操作。要判断，必须回当前代码重判。

可能出现：
```text
平台 IGNORED + 本地 CONFIRMED      → 忽略只是流程动作；问题成立仍需决定是否修
平台 IGNORED + 本地 DISMISSED      → 一致：本地找到反证，当初不该按“真缺陷”处理
平台 CLOSED_NOT_ADOPTED + 本地 CONFIRMED → 仍需决定是否修
平台 PENDING + 本地 NEEDS_EVIDENCE → 还不能下结论
```
不要用平台状态反推本地判断，不要把 `adopt` 当成“已修好”，也不要把 `IGNORED` 当成“同事认可 / 误报”。最终报告里 `Platform` 与 `Local` 分开写。

## 处理动作
默认先做修前分析、由用户决策，再进入代码执行。只有用户明确要求“直接修”时才可跳过 HTML；跳过时仍要保留修前判断与证据。不要求每条 finding 都走完整流程。

> 文末的 Reference routing 表是索引；实际执行时以各阶段末尾的链接作为加载触发点。

### 1. 修前分析（不改代码）
- **读取当前事实**：拉取 AI 评论，确认 MR 状态、目标分支、本地 HEAD 与评论的 `context` 是否一致；读取相关 diff 与代码。
- **生成 artifact 骨架**：
  ```bash
  python3 <本 Skill 所在目录>/scripts/review.py artifact \
    --repo <repo> --mr <id> --worktree <目标 worktree> [--state all] [--force]
  ```
  默认落 `.engineering/work/ai-review/<repo__mr__head>/review.json`。试点可加 `--ids <note-id,...>`，只生成指定 Finding；artifact 会记录 `selection.mode=ids`，HTML 提示这不是全量评审。同一 `reviewKey` 下的后续全量 artifact 会复用未变化 Finding 的决策。脚本对任意平台状态都可拉取并重分析（含已忽略 / 已处理 / 已合并 MR）：`--state all` 把全部评论纳入可分析 active findings，`--state ignored` / `closed` / `handled` 按状态选，默认 `pending`。**默认只把 pending 当 active、其余进 `closedFindings` 只读汇报**——这是目标缺省而非能力上限；是否重分析已忽略 / 已处理由你按目标决定，用 `--state` 选择即可（`--include-closed` 为 `--state all` 别名）。目标文件已有 analysis 时默认拒绝覆盖；用 `--out` 生成新文件，只有明确要丢弃旧分析时才加 `--force`。这是一次性执行产物，**只落在 `.engineering/work/` scratch 区，不写入 canonical 区、不走项目归档规范，也不为“只要文档”额外写说明文档**。
- **并行分析**：互不依赖的 finding 可以并行 / 分批分析，不需要串行。并行 worker 只返回 `{id, set}` patch fragment，不直接写 `review.json`；由主 Agent 合并后用一次 `patch` 写入。只有同一根因 / 同一 owner 且结论互相依赖的 finding 才需要合并处理。
- **只有已关闭项**：如果 artifact 的 `findings=[]`、`closedFindings` 非空，不进入分析 / 决策，直接生成 HTML 汇报页；需要重分析时用 `--state all` 重新生成。
- **用 patch 写 analysis**：不要整份重写 `review.json`。模型只生成字段 patch，由脚本校验、重算指纹并原子写入：
  ```bash
  python3 <本 Skill 所在目录>/scripts/review.py patch \
    --artifact .engineering/work/ai-review/<slug>/review.json \
    --patch .engineering/work/ai-review/<slug>/analysis-patch.json
  ```
  支持批量 Finding 和 `proposal.summary` 这类点路径；数组字段整体替换；人工决策字段禁止写入。并行 worker 的多个 fragment 可重复传 `--patch`，由脚本一次性合并校验。完整格式见 [references/review-artifact.md](references/review-artifact.md)。
- **逐条判断（可并行）**：按 claim 类型验证，填 `assessment / recommendation / issueRisk / trigger / impact / rootCause / evidence / openQuestions / proposal`；`proposal` 内用 `fixRisk`。判断依据见 [references/triage.md](references/triage.md)，修复范围、Owner、验证与停止条件见 [references/verification.md](references/verification.md)。
- **只做分析**：本阶段可以运行只读测试 / 命令来验证 claim，但不修改代码、不提交、不推送；`CONFIRMED` 只代表问题成立，不代表已经修好。跨模块 / 高成本项在 `proposal` 中写清范围与验证，先等用户决策，不在分析阶段直接改。
- **生成 HTML**：
  ```bash
  python3 <本 Skill 所在目录>/scripts/review_html.py \
    --artifact .engineering/work/ai-review/<slug>/review.json
  ```
  Builder 会校验 artifact；缺 analysis 或指纹不一致时拒绝生成。

### 2. 人工决策
- 打开 `review.html`，执行授权只有两个动作：**批准修复（`APPROVE`）** 或 **关闭评论（`CLOSE`）**；列表操作列另有**退回重评**入口（写入 `PROVIDE_INFO`，必填理由，把补充信息或纠正意见交回 Agent 重新评估整条 Finding；非终局、不构成执行授权），详情页还可**暂不处理（`DEFER`）**。每个人工动作都可就地撤销（取消批准 / 取消退回 / 取消关闭 → `UNDECIDED`，覆盖 AI 默认），顶栏「恢复 AI 默认决策」整页重置——确认框先展示恢复后的授权分布（含"此前被你否决过、将重新获得批准"的条数），防止"清空"动作在人类认知里变成静默重新授权。AI 推荐（FIX→`APPROVE`；DISMISS/DEFER→`CLOSE` 并自动带 AI 理由）**默认选中即生效**，人只扫一眼、改例外；无 AI 推荐（NEEDS_EVIDENCE / 无可行方案）或显式清除的条目才停在未决策。
- `APPROVE` 必须对应有效的 FIX 方案；`CLOSE` 必须填写理由（`note`）。不满足按 `INVALID` 处理，不授权。要换方案就回改 `review.json` 让 `proposalFingerprint` 变化、旧授权自动 stale，再重新批准，不设独立“调整”态。
- 人工结局四类：`APPROVE`（授权修复）、`CLOSE`（结束评论，必填理由）、`DEFER`（暂不处理）、`PROVIDE_INFO`（人工补充信息、要求 Agent 重新评估整个 Finding，需非空 `note` 或至少一个 `answers`；列表「退回重评」与详情页「补充信息 · 重新评估」都是该状态，均不构成执行授权）。`DEFER` / `PROVIDE_INFO` 是有效决策但**非执行授权**，不进入 `AUTHORIZED`。`UNDECIDED` 仍只代表“尚无有效授权”，不会执行。
- 自由输入（`note`）是一等决策上下文，不是备注：缺外部信息时它是主入口（可一句话纠正 Agent 的整体判断、推翻问题前提），有方案时用于补充执行要求或异议；结构化 `answers` 可选、可只答部分；关闭直接复用同一 `note` 作为理由，不重复填写。
- `NEEDS_EVIDENCE` 表示**调查已达仓库知识边界**（有效调查结果，而非“未调查”）：界面以「当前可确定 / 缺少的外部信息 / 为何影响判断 / 需要人工提供」呈现，不提示“继续让 Agent 调查”（无新信息时重复调查无意义）。
- 在 FIX 的 `proposal.requiresHumanAcceptance` 中明确判断执行后是否保留人工验收义务：依据实际无法覆盖的重要结果或用户要求，具体义务写入 `verification`；不由风险档位、scope 或验证文本关键词推导。HTML 只读展示并随 APPROVE 的 Envelope 携带同值，check-envelope 校验一致性。该字段受 proposalFingerprint 保护；旧方案缺字段时保守显示需补评，不默认为自动验证充分。
- 决策只存浏览器本地存储（LocalStorage），作为当前评审的界面草稿，不是项目状态，也不是第二份评审权威；点击“生成交接”得到 Decision Envelope。**不要求用户维护 `decisions.json`。**
- `reviewKey = <repo>#<mergeRequestId>` 稳定关联评审；`proposalFingerprint` 覆盖问题有效性、根因 / 证据、问题风险与 proposal。方案变化的 Finding 单独标 stale；旧决策保留供查看，但缺失或过期指纹不授权。
- 重新生成 artifact 时，目标文件已有 analysis 默认拒绝覆盖；不会静默清空。

### 3. Coding Agent 执行
- 把 Decision Envelope 粘贴给 Coding Agent，并提供 `review.json` 路径。
- 先校验：
  ```bash
  python3 <本 Skill 所在目录>/scripts/review.py check-envelope \
    --artifact .engineering/work/ai-review/<slug>/review.json \
    --envelope .engineering/work/ai-review/<slug>/envelope.json
  ```
  Envelope 可由 Agent 从粘贴内容保存为执行留痕；它不是用户必须维护的第三份文件。
- 只执行 `AUTHORIZED` 项：`APPROVE` 改代码、`CLOSE` 不改代码（只结束评论）。`STALE` 只停该条并要求重新决策；`INVALID`（含 `CLOSE` 缺理由）不执行。`STALE` 不阻断其他 Finding。
- 只执行授权动作：不把 `CLOSE` 变成改代码，也不把 `APPROVE` 扩大成无关重构。
- 执行前核对代码与证据是否仍适用；`headMatches=false` 或 `branchMatchesSource=false` 只是预检信号，不能替 Agent 做准入判断，也不能只看 SHA。
- 修改后按 `proposal.verification` 验证，输出执行报告。执行范围、证据强度、何时停止或交回上游见 [references/verification.md](references/verification.md)。
- 执行后处置按已核验的 `requiresHumanAcceptance`（旧 Envelope 缺字段先补评，不默认为 false）：`true` → 自动验证通过后**停下等人工验收**，不标完成；`false` → AI 自验后完成，但自验必须说明验证覆盖了什么、结果如何、是否符合批准的修复方案（不是只跑命令）。
- 验证失败或无法提供充分证据 → 不标完成，先修复或报告阻塞。实施中需实质偏离人工授权方案 → **重新请求决策**，不得先做未授权修改再事后补确认（超出授权是决策问题，不是验收问题）。

### 4. 平台反馈（独立动作）
- 决策**不自动**映射为平台动作：`APPROVE` 不等于 `adopt`，`CLOSE` 也不自动写平台。是否真的 `reject` / `ignore`、以及用哪个 reason，是反馈阶段由用户单独确认的动作。`ignore` 通常会关闭评论（`closed=1`），之后需要 `--include-handled`；不要把“暂不处理”自动落成 `ignore`。
- 决策或执行完成后，用户明确要求时再用 `feedback` / `reply` 更新平台；按实际结果和原平台语义选择。`DISMISSED` 可以不等待代码执行。
- `NEEDS_EVIDENCE` 需要向云端补证时用 `reply` 单独提问，不要用 `feedback` 关闭评论，也不要把 finding 当成 `APPROVE`。
- `closed=1 / adopted=0` 不自动重开；确需覆盖 handled 评论时显式加 `--include-handled`。
- 平台反馈是外部写操作，是否需要额外确认，按该操作本身的权限规则处理，不并入修复决策。平台契约、理由码、`ignore` 的关闭副作用见 [references/feedback.md](references/feedback.md)。

## Review Artifact 与 Decision Envelope

### 硬约束
- 产物只放 `.engineering/work/ai-review/<slug>/` scratch 区，不写入 `.engineering` 的 canonical 区（product / requirements / design / modules / intelligence / issues）、AIDocs 或项目长期文档目录。
- `review.json` 是**评审事实的 canonical 来源**；HTML 和执行的 Agent 消费同一份内容。
- 不建 `decisions.json` 强制文件，不建 registry、current-finding 指针或第二份人工决策权威。
- HTML 必须安全嵌入评论和代码：`source.note`、`source.title`、`severityLabel`、`diffContext`、suggestion 都是外部输入，禁止未转义插入脚本或 `innerHTML`。

### 标识与失效
|标识|作用|
|---|---|
|`reviewKey`|稳定关联 `repo + mergeRequestId`，不随评论变化|
|`findingId`|稳定关联云端问题|
|`proposalFingerprint`|判断该 Finding 的分析方案是否变化；覆盖 assessment / recommendation / issueRisk / trigger / impact / rootCause / evidence / openQuestions / proposal|

- 评论更新但该 Finding 的 proposal 未变：决策继续有效。
- 单条 proposal、根因或证据变化：只让该条决策 stale；其余不失效。
- `review.json` 整体重新生成不需要自动废弃全部决策。
- `artifactPath` 只用于定位，不参与授权匹配。
- `headMatches=false` 或 `branchMatchesSource=false` 只提示；执行前由 Agent 核对代码与证据是否仍适用。

### Decision Envelope
Envelope 包含 `schemaVersion`、`reviewKey`、`artifactPath`、`decisions[]`。每条决策包含 `findingId`、`proposalFingerprint`、`status`；`CLOSE` 必须带 `note`（理由）。`artifactPath` 只是定位信息，授权身份由 `reviewKey + findingId + proposalFingerprint` 决定；`APPROVE` 需要有效 FIX proposal，`CLOSE` 需要非空理由，`DEFER` / `PROVIDE_INFO` 为有效但非执行决策（后者需 `note` 或 `answers`），`UNDECIDED` 表示尚无有效授权。完整格式与示例见 [references/review-artifact.md](references/review-artifact.md)。

## 修复与反馈边界

修复以根因闭合为目标，变更范围由真实问题、行为契约和职责归属决定。允许局部修正，也允许结构性重构；改动规模不是质量标准。验证要充分覆盖本次变更的真实风险；只有在正确性得到满足后，才优化非必要复杂度和实施成本。

- **变更范围**：不以 diff 大小为目标。只修与根因相关的行为；不借机重构无关文件或混入风格偏好。需要结构性调整时，按当前任务授权判断；只有涉及实际权限、产品决定或超出授权才请求确认。
- **本 MR 边界**：确认问题是本 MR 引入还是既有问题。既有问题若不在当前交付范围，默认 `CONFIRMED + DEFER`；只有安全 / 正确性风险且当前 MR 已经触碰相关 owner 时，才考虑在本 MR 修。
- **产品决策缺口**：如果 finding 的成立依赖“产品应该怎样”，先读已有的 clarification / design / PRD 或询问用户；**缺少 PRD 本身不是阻塞**，技术性 finding 仍可直接用代码、Diff、测试和工程契约处理。不要自行发明产品语义。
- **大范围改动**：跨模块重构、数据迁移、API 契约变更、权限模型调整，按当前任务已授权范围判断是否直接做；涉及实际权限、产品决定、跨团队影响或超出授权时，停下来说明原因与建议路径。
- **提交边界**：可以修改工作区代码并运行验证；`commit` / `push` / 合并 / 批准只在用户明确要求时执行。
- **执行异常才回退**：只有方案偏离、技术阻塞、超出授权、事实变化或验证失败时，才把该 Finding 交回用户；正常完成不需要第二轮逐项验收。
- **反馈不是关闭**：`operate_ai_comment` 成功只代表反馈已提交。代码是否修好由本地验证决定，问题是否关闭由平台状态决定；两者都不能互相代替。
- **回复要有证据**：回复云端时写清触发条件、影响、实际改动与验证结果；不要只写“已修复”“误报”或长篇辩护。
- **不维护项目级本地状态**：不在 `.engineering` canonical 区建 AI review 状态文件、registry 或 current-finding 指针（scratch 只落 `.engineering/work/`，可丢弃、不作为跨任务状态）。浏览器 LocalStorage 只是当前评审的决策草稿，不是项目状态；需要恢复时重新拉取评论、读取当前代码与平台状态。
- **不刷屏**：每轮只回复有新增证据的内容；云端重复同一观点且没有新证据时，停止循环并报告分歧。

## 多轮复审
云端 Agent 可能回复质疑、补充场景或重新打开同一问题。多轮处理的规则：
- **重新验证，不为旧结论辩护**：以最新代码、Diff、运行结果为准；上一轮的 `DISMISSED` 可以被新证据推翻，上一轮的结论也可能因为后续改动失效。
- **对准争议前提**：把分歧拆成“触发条件是否可达”“影响是否成立”“是否本 MR scope”“修复成本是否值得”中的具体一项，用证据回答，不泛泛争论。
- **云端正确时直接承认**：更新判断，必要时重新生成 artifact/HTML；不要为了维持之前的判断而找理由。
- **没有新证据就停**：如果云端只是重复原观点，或继续要求与本 MR 无关的改动，记录分歧、当前证据与未决问题，交给用户决定。
- **读取回复的限制**：当前 `code` 服务主要暴露 AI 评论列表与评论创建；如果没有可直接读取回复线程的工具，优先尝试现有评论列表，仍拿不到就请用户粘贴云端回复或提供 MR 页面内容，不猜测对方说了什么。

## 工具
脚本只做数据读取、artifact 生成、结构校验和 CRUD 封装，不替你判断 finding 是否成立。以下命令在**目标项目 worktree** 内执行，`<本 Skill 所在目录>` 指本 Skill 的安装路径：
```bash
# MR 基本信息与变更规模（确认 repo / id / iid / 状态 / MR 链接）
python3 <本 Skill 所在目录>/scripts/review.py mr --repo <repo> --mr <id>

# 待处理 finding（默认只列 pending；也支持 --state all / --severity / --path / --limit / --json）
python3 <本 Skill 所在目录>/scripts/review.py list --repo <repo> --mr <id>

# 单条完整内容、diff 上下文与 suggestion
python3 <本 Skill 所在目录>/scripts/review.py show --repo <repo> --mr <id> --id <note-id>

# 生成 review.json 骨架（不修改代码；默认已关闭项只汇报）
python3 <本 Skill 所在目录>/scripts/review.py artifact --repo <repo> --mr <id> \
  --worktree <目标 worktree> [--ids <note-id,...>] [--state all] [--force]

# 用字段 patch 批量更新 analysis（可重复 --patch 合并并行 fragment）
python3 <本 Skill 所在目录>/scripts/review.py patch \
  --artifact .engineering/work/ai-review/<slug>/review.json \
  --patch .engineering/work/ai-review/<slug>/analysis-patch-a.json \
  [--patch .engineering/work/ai-review/<slug>/analysis-patch-b.json] \
  [--dry-run] [--allow-incomplete]

# 生成 HTML 决策页
python3 <本 Skill 所在目录>/scripts/review_html.py \
  --artifact .engineering/work/ai-review/<slug>/review.json

# 校验 Decision Envelope 与 artifact 是否一致
python3 <本 Skill 所在目录>/scripts/review.py check-envelope \
  --artifact .engineering/work/ai-review/<slug>/review.json \
  --envelope .engineering/work/ai-review/<slug>/envelope.json

# 平台反馈（默认 dry-run；加 --confirm 才写入；覆盖 handled 用 --include-handled）
python3 <本 Skill 所在目录>/scripts/review.py feedback --repo <repo> --mr <id> --id <note-id> \
  --action adopt|ignore|reject [--reason-code <code> | --reason <text>] [--confirm]

# 平台回复（默认 dry-run；加 --confirm 才写入）
python3 <本 Skill 所在目录>/scripts/review.py reply --repo <repo> --mr <id> --id <note-id> \
  --note-file <file> [--confirm]
```
`--repo` 可省略，从当前 worktree 的 `origin` 推断。如果不在目标 worktree 内执行，显式传 `--repo` 与 `--worktree <目标 worktree>`，否则 HEAD 对比会落到插件目录。写操作不会自动重试，避免重复反馈；脚本会在写入前重新拉取并拒绝处理已经 handled 的评论（确需覆盖时用 `--include-handled`）。`--json` 只输出纯 JSON，诊断信息走 stderr。

## Reference routing
|当前问题|读|
|---|---|
|看不懂某个术语（Status、Basis、Binding、五个面、Scope / Rigor、AC / P 等）|[references/glossary.md](references/glossary.md)|
|review.json 字段、assessment/recommendation、closedFindings、并行 patch、proposalFingerprint、Decision Envelope、HTML 契约|[references/review-artifact.md](references/review-artifact.md)|
|一条 finding 如何验证、如何区分严重性与决策、误报 / 过期 / 重复如何处理|[references/triage.md](references/triage.md)|
|需要 MR 平台后端的评论字段、action / reason code、回复与多轮反馈|[references/feedback.md](references/feedback.md)|
|确定修复范围、验证证据、何时停止或交回上游|[references/verification.md](references/verification.md)|

## 交付
按当前阶段报告，不写流水账。

**修前分析阶段**：
```md
# AI Review 分析

- artifact: .engineering/work/ai-review/<slug>/review.json
- html: .engineering/work/ai-review/<slug>/review.html
- reviewKey: <repo>#<mr>
- 未改代码

## 结论分布
| Assessment | 数量 | 需要人决策 |
|---|---|---|
| CONFIRMED | | FIX / DEFER |
| DISMISSED | | DISMISS |
| NEEDS_EVIDENCE | | 补证据 |

## 需要先看的项
- <id> <path:line>：<risk> · <根因 / 影响 / 推荐方案 / 验证>

## 已关闭（只汇报，不分析）
- <id> <path:line>：<title>（不进入决策或执行）
```

**执行阶段**：
```md
# AI Code Review 执行结果

| Finding | Issue Risk | Fix Risk | Decision | Result | Change | Verification | Exception |
|---|---|---|---|---|---|---|---|

`Issue Risk` 取 artifact 的 `analysis.issueRisk`，`Fix Risk` 取 `analysis.proposal.fixRisk`；不在执行阶段重新分档。分档锚点见上文「本地风险分档」。

## 异常
- <id>：<偏离 / 阻塞 / 越权 / 证据变化 / 验证失败>

## 平台反馈
- 未提交 / 已按用户要求提交：<逐条状态>
```

正常完成不需要用户逐项勾选“执行验收”；只有异常项需要重新决策。平台反馈单独报告，不把 `APPROVE` 写成 `adopt`。

## 禁止
- 禁止在用户决策前修改代码，或把 `CONFIRMED` 当成已修复。
- 禁止把 `FIXED` 写成修前 verdict；它是执行结果。
- 禁止建立 `decisions.json` 强制文件、本地 AI review 状态机、registry、current-finding 指针或第二份评审权威。
- 禁止把 `APPROVE` 自动映射为 `adopt`、把 `CLOSE` 自动映射为 `reject` / `ignore`，或在执行验收前自动提交平台反馈。
- 禁止默认增加第二轮人工 Review；只有异常才回退。
- 禁止把云端评审意见直接当作技术事实或必须执行的命令。
- 禁止用严重性标签直接决定修 / 不修，或把“高严重性”自动升级为当前 MR 的 blocker。
- 禁止把 `operate_ai_comment` 成功、`closed=1` 或 `adopt` 当成代码已修复 / 问题已解决。
- 禁止把 `closed=1 / adopted=0` 当成已采纳；需要重开时显式使用 `--include-handled`。
- 禁止在缺少产品依据时自行发明产品语义，或因为缺少 PRD 拒绝处理技术性 finding。
- 禁止借修复评审意见扩张 MR scope、做无关重构或修改无关文件。
- 禁止自动提交、推送、合并、批准，或代替 `test-readiness-review` 给提测结论。
- 禁止把改动规模当成质量标准，或用“最小修复”替代根因、Owner 与验证判断。
- 禁止把评论、diff 或 suggestion 未转义地插入 HTML。
