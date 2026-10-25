# 平台反馈与多轮复审
本文件记录 MR 平台后端上 AI 评审评论的实际契约，以及本地判断如何落到平台动作。平台状态是远程事实，本地 assessment / 执行结果是技术事实，修复决策又是另一层授权；三者不能互相代替。

## 1. 前置条件
本副本不内置平台客户端。所有远程动作经由 `scripts/mr_backend.py` 的
`run_tool(name, payload, retry=...)`——它是唯一需要你替换的传输层，工具契约见该文件头部。

- 接入前先确认三件事：身份可用、读权限（评论 / MR 详情 / 变更文件）、写权限（操作评论 / 新建评论）。
- `run_tool` 收到 `retry=False` 时必须不重试；写操作重复提交会产生重复评论。
- `repo` 是仓库路径，例如 `acme/webapp`，不是完整 URL；脚本会从 SSH / HTTPS remote 归一化。
- `mergeRequestId` 是**项目级 `id`**（例如 `42188`），不是列表里的 `iid`（例如 `711`）。传错会查不到或查到别的 MR。
- 服务错误可能是纯文本（如 `Repository(...) not found`），不一定是 JSON；脚本会把原始错误显示出来。
- 读操作可重试；写操作不自动重试，避免重复评论 / 重复反馈。

## 2. 读取 AI 评论
`list_merge_request_ai_comments(repo, mergeRequestId)` 返回一个数组（不是分页对象）。实际观察到的字段：
```json
{
  "id": 904201,
  "note": "![缺陷 · 中](...)\n\n`onCommit` 可能拒绝输入……",
  "path": "src/pages/.../fields.tsx",
  "line": 46,
  "lineRange": {"fromLine": 46, "toLine": 46},
  "originLineRange": {"fromLine": 46, "toLine": 46},
  "side": "right",
  "context": "<old-sha> <new-sha>",
  "outdated": false,
  "closed": 0,
  "adopted": 1,
  "parentNoteId": null,
  "notesCodeDiffContext": "@@ ...",
  "suggestion": {"id": 1, "noteId": 904201, "diff": "@@ ...", "applied": false},
  "coAuthor": {"username": "codereview-copilot"},
  "aiComment": true,
  "createdAt": 1792402320000,
  "updatedAt": 1792402320000
}
```
状态观察（`platform_interpretation` 是唯一映射源，CLI / Artifact / HTML 只消费它的结果，不各自解读 adopted/closed）：
- `closed == 0 且 adopted == 1` → **PENDING**：尚未处理。
- `closed == 1 且 adopted == 0` → **CLOSED_NOT_ADOPTED**：已关闭但未采纳，不等于已修复，也不等于误报。
- `closed == 1 且 adopted == 3` → **IGNORED**：目标平台 UI 显示“已忽略”。
- `closed == 1 且 adopted == 2 / 4` 等 → **CLOSED_WITH_ACTION**：已知已处理、具体动作未观测，不猜测。

`IGNORED` 的证据范围：仅在**单个 MR 的 19/19 条 `adopted=3 / closed=1`** 上观测到 UI 显示“已忽略”。由此**不能**推出——所有 `adopted=3` 都是忽略、`adopted=2/4` 分别是什么、被忽略意味着误报、或全部忽略就是有人做了批量操作。它是一个流程动作，不是技术结论。

不要把 `adopted != 1` 直接解释成“已修复”；不要把 `已忽略` 解释成“同事认可 / 误报”。`IGNORED` 在平台上把“问题不成立（应为误报）”和“成立但暂不修（真正的 ignore）”合并进同一档，从平台状态读不出技术信息——必须回当前代码重新判断。其他未列出的取值组合按 `UNKNOWN` 对待，重新拉取或查 MR 页面确认。

补充工具：
- `list_merge_request_comments(repo, mergeRequestId, page?, pageSize?)`：实际观察到它只返回未处理的 AI 行内评论（`field` 为 `body` / `filePath` / `lineNumber`）。它可以用来确认某条 pending 评论是否仍在，但不能假设它一定能读到回复线程。
- `get_merge_request_detail(repo, mergeRequestId)`
- `list_merge_request_changed_files(repo, mergeRequestId)`
- `get_merge_request_changed_file_diff(repo, mergeRequestId, oldPath, newPath)`
- `list_merge_request_commits(repo, mergeRequestId)`

这些用于确认 MR 状态、变更范围和评审上下文；本 Skill 不重复实现 GitLab 数据层。

`update_merge_request_comment_status(repo, mergeRequestId, noteId, closed?)` 这个工具只改**通用评论**的 `closed` 状态，不记录 `adopt / ignore / reject`，不能替代 `operate_ai_comment`。不要用它把 AI 评论“做成已关闭”；只有用户明确要求解决某个普通评论线程时才使用。

## 3. 提交反馈
`operate_ai_comment(repo, mergeRequestId, noteId, action, reason?)`

### action 是平台动作，不是修复决策
|action|语义|何时使用|
|---|---|---|
|`adopt`|采纳 AI 建议|代码已实际修改并完成必要验证后|
|`ignore`|忽略 / 暂不处理|真实但当前不处理，或不打算在本 MR 处理|
|`reject`|拒绝 / 不接受建议|有证据表明不成立、不适用或当前代码已解决|

人工在 HTML 中的 `APPROVE / CLOSE / UNDECIDED` 不是平台动作：

- `APPROVE` 只授权按方案改代码，不自动等于 `adopt`。
- `CLOSE`（必填理由）只表示“不改代码、结束该评论”，不自动写平台；真正 `reject` 还是 `ignore` 由反馈阶段按理由单独确认。
- `UNDECIDED` 没有授权（未处理或被 stale / invalid 降级），不应产生平台动作。

平台反馈是在决策或执行之后、由用户明确要求的独立动作。执行结果和原平台语义一致时，再由用户决定提交；不要从 Decision Envelope 自动推导，也不要把 DISMISSED 的反馈强行等到“代码执行”之后。

`ignore` 动作会使评论变成 handled（`closed=1`），之后要再处理必须显式 `--include-handled`。具体落到的 `adopted` 数值本 skill 未独立验证（读侧“已忽略”观测为 `adopted=3`，但不假定写动作与之相同）；提交后用 `list --json` 回查实际 `adopted / closed`。不要把“暂不处理”自动落成 `ignore`；如果用户只是现在不修、但希望保留可处理性，优先不提交平台动作，或明确说明关闭评论的代价。

`NEEDS_EVIDENCE` 的补证问题用 `reply` 单独提出；`reply` 是评论动作，不等于 `operate_ai_comment` 的 adopt / reject / ignore，补证时不要用 `feedback` 关闭评论。

不要这样用：
- 用 `adopt` 表示“我看到了，但还没修”；
- 用 `reject` 表示“我不想改”；
- 用 `ignore` 表示“误报”；
- 在证据不足时随便选一个动作把评论清掉。

### reason code
`reason` 可选，优先用内置 code；没有匹配再传自由文本。脚本要求 `ignore` / `reject` 必须给出 code 或文本；`adopt` 通常不需要 reason（修复证据放在回复里），脚本只拒绝 adopt 的 reason code，允许自由文本补充说明。

`reject` 可用：
|code|适用|
|---|---|
|`AI_MISJUDGED`|AI 误判 / 理解错误|
|`SCENARIO_IMPOSSIBLE`|实际场景下不可能触发|
|`NOT_APPLICABLE`|语言 / 框架 / 文件不适用|
|`RULE_DISAGREE`|不认同该规则|
|`MY_IMPL_BETTER`|当前实现更优|
|`SUGGESTION_POOR`|建议不可行|

`ignore` 可用：
|code|适用|
|---|---|
|`LOW_PRIORITY`|优先级低|
|`KNOWN_ISSUE`|已知问题，暂不修复|
|`TEMP_CODE`|临时 / 实验代码|

选择原则：code 只做分类，具体证据仍要写在回复里。例如 `SCENARIO_IMPOSSIBLE` 必须说明为什么不可达；`KNOWN_ISSUE` 要给出后续条件或已有记录。

**“已由后续提交修复”没有完全匹配的内置 code**：用 `--reason` 自由文本写“当前代码已修复（评论基于旧提交）”，附当前文件 / symbol 定位；不要硬套 `AI_MISJUDGED`，也不要把“评论过时”说成“AI 误判”。这种情况用 `reject` 表示该 finding 对当前代码不再适用，不要用 `adopt` 冒充“本次修复”。

### 调用示例
以下命令在目标项目 worktree 内执行；`<本 Skill 所在目录>` 为本 Skill 的安装路径。
```bash
# dry-run：只打印 payload，不写入
python3 <本 Skill 所在目录>/scripts/review.py feedback --repo acme/webapp \
  --mr 42188 --id 904201 --action reject --reason-code AI_MISJUDGED

# 确认后写入
python3 <本 Skill 所在目录>/scripts/review.py feedback --repo acme/webapp \
  --mr 42188 --id 904201 --action reject --reason-code AI_MISJUDGED --confirm
```
脚本在写入前会重新拉取该评论：
- 已经是 handled 时默认拒绝，避免重复反馈；确需覆盖时显式用 `--include-handled`；
- 找不到 note id 时直接报错，不猜测；
- 写操作不自动重试；失败时保留原始错误，待冷却后人工重跑。

### 3.1 修复决策与平台反馈分离

修复决策由 `review.html` 产生，平台反馈由 `feedback` / `reply` 产生，两者是不同权威：

```text
人工决策：APPROVE / CLOSE / UNDECIDED
代码执行：IMPLEMENTED / BLOCKED / DEVIATED / VERIFY_FAILED
平台动作：ADOPT / REJECT / IGNORE / NONE
```

- 不建 `decisions.json` 强制文件；Decision Envelope 是复制给 Agent 的授权内容。
- 不把 Decision Envelope 直接交给批量平台反馈；平台反馈按实际执行结果逐条处理。
- 全部评论都是 `CLOSED_NOT_ADOPTED` 时，仍可分析和决策；要覆盖 handled 评论时显式加 `--include-handled`。
- 平台可能拒绝重新打开 handled 评论；失败时如实报告，不把本地状态写成已采纳。

## 4. 回复云端
`comment_merge_request(repo, mergeRequestId, note, parentNoteId?)`

- `parentNoteId` 必须是**顶层评论**；AI finding 通常是顶层评论，可以回复。
- 不能回复一条已经是回复的评论（不支持嵌套回复）。
- 回复内容要能被独立阅读：本地判断、触发条件、证据、改动、验证结果、后续条件。
- 长日志不要整段粘贴；给出命令、关键输出、文件 / symbol 或运行观察。

建议结构：
```text
Local assessment: CONFIRMED / DISMISSED / NEEDS_EVIDENCE
Execution result: IMPLEMENTED / NOT_CHANGED / BLOCKED（若已执行）
Trigger: <可达 / 不可达，为什么>
Impact: <实际影响或为什么没有影响>
Change: <文件 / symbol + 改动摘要，若有>
Verification: <命令 + 结果，若有>
Next: <后续条件，或需要云端补充的证据>
```
示例（误报）：
```text
Local assessment: DISMISSED
Trigger: 该分支不可达。`onCommit` 的调用方已在 `CourseForm` 对 `courseId` 做非空校验，
空值会在提交前被拦截；当前 MR 也没有新增绕过该守卫的入口。
Evidence: `src/.../CourseForm.tsx:100`（校验）、`src/.../fields.tsx:46`（评论落点）。
```
示例（已执行）：
```text
Local assessment: CONFIRMED
Execution result: IMPLEMENTED
Change: `fields.tsx` 的 `onCommit` 现在返回成功与否；拒绝时恢复字段原值。
Verification: `npm test -- course-form` 通过；手动路径：空 id 失焦后恢复原值。
```

## 5. 状态核对与“反馈不等于关闭”
反馈成功后必须重新拉取一次：
```bash
python3 <本 Skill 所在目录>/scripts/review.py list --repo <repo> --mr <id> --state all --json
```
确认：
- 该 note 的 `closed` / `adopted` 是否变化；
- MR 上是否出现新的 AI 评论（云端可能重新生成 finding）；
- 代码是否仍然保持修复（后续提交可能回退）。

报告里分开写 `Platform`（取 `platform_interpretation`）与 `Local`（assessment / 执行结果），例如：`Platform: IGNORED（closed=1, adopted=3）/ Local assessment: CONFIRMED`，或 `Platform: PENDING / Local assessment: NEEDS_EVIDENCE`。禁止写成“已关闭（因为 operate_ai_comment 成功了）”“已修复（因为平台显示 closed）”“已忽略（所以是误报）”。

平台 `closed` 只说明评论线程被处理，不证明代码行为正确；本地 `IMPLEMENTED` 只说明当前验证通过，不说明云端已认可。`closed=1 / adopted=0` 必须单独标注为未采纳。

## 6. 多轮复审
云端 Agent 可能：
- 回复质疑本地结论；
- 补充新的触发场景；
- 重新生成同一文件的 finding；
- 在代码更新后产生新的评论。

处理规则：
1. **重新拉取**：不要依赖上一轮的内存或本地临时记录；以最新 `list_merge_request_ai_comments` 为准。
2. **识别轮次**：同一 `id` 的内容 / `updatedAt` 变化是复审；新 `id` 是新 finding，按新问题处理。
3. **重新验证**：以当前代码、Diff、测试为准。上一轮的 `DISMISSED` 可以被新证据推翻；上一轮的 `IMPLEMENTED` 也可能因为后续改动失效。
4. **对准争议前提**：把分歧拆成触发条件、影响、scope、修复成本中的具体一项，用证据回答。
5. **云端正确就更新**：修改 assessment / 决策 / 执行结果，重新生成 artifact/HTML；不要为了面子维持旧结论。
6. **没有新证据就停**：云端重复同一观点时，记录分歧与当前证据，交给用户；不要无限循环。

当前 MCP 面没有明确的“读取回复线程”工具。`list_merge_request_comments` 只观察到未处理的 AI 评论；如果读不到云端回复，请用户粘贴回复或提供 MR 页面内容，不要猜测。

## 7. 失败与降级
|情况|处理|
|---|---|
|`mr_backend.run_tool` 未实现 / 身份未登录|实现后端并确认授权；不要绕过 `run_tool` 直连|
|读/写权限不足|按平台授权流程补齐；仍失败则报告，不继续写操作|
|repo / MR 找不到|检查 repo 路径与项目级 `id`；必要时用 `list_repo_merge_requests` 核对|
|空列表|可能没有 AI 评论，也可能都已 handled；用 `--state all` 或 MR 详情区分，不直接说“没有问题”|
|网关限流|读操作自动重试；写操作等冷却后人工重跑，不自动重试|
|JSON 输出损坏|读操作重试一次；写操作不重试，避免重复写入|
|MR 已合并 / 已关闭|仍可只读分析；平台可能拒绝反馈，先确认状态再决定是否只出报告|
|本地不是 MR 分支|先确认 / 切换用户指定的 worktree；不要擅自 checkout 或覆盖未提交改动|
|反馈成功但状态未变|重新拉取确认；仍不变则记录平台限制，不宣称已关闭|
|评论已是 handled|默认跳过；确需覆盖时用 `--include-handled`，并记录覆盖风险|
