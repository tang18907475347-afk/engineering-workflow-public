# Review Artifact 与 Decision Envelope

本文只定义数据契约和产物边界，不替代 finding 的判断规则。finding 是否成立看
`triage.md`，修复范围与验证看 `verification.md`。

## 1. 产物

```text
.engineering/work/ai-review/<repo__mr__headShort>/
  review.json     评审事实与修前分析，canonical
  review.html     从 review.json 派生的本地决策界面
```

- 只落 `.engineering/work/` scratch，不写入 canonical 区、不写 AIDocs、不建 `decisions.json`。
- `analysis-patch.json` 是模型交给脚本的临时输入，不是 canonical 产物，可随时删除。
- `review.html` 可以随时删除并重建；人工决策在浏览器的
  `localStorage["ai-review:<reviewKey>"]` 中。
- Decision Envelope 在点击“生成交接”时产生，复制给 Coding Agent；Agent
  需要留痕时可自己保存为 `envelope.json`，但这不是用户必须维护的文件。

## 2. Review Key 与 Proposal Fingerprint

```text
reviewKey = <repo>#<项目级 mergeRequestId>
```

`reviewKey` 不包含评论更新时间、HEAD 或报告版本。评论变化时，只有
`proposalFingerprint` 变化的 Finding 需要重新确认。

`proposalFingerprint` 覆盖会影响授权语义的分析内容：

```text
sha256(canonical_json({
  assessment, recommendation, issueRisk,
  trigger, impact, rootCause,
  evidence, openQuestions, proposal
}))[:16]
```

因此问题是否成立、根因 / 证据 / 问题风险变化、方案或修复风险变化，都会让旧授权失效。不覆盖 `source.note`、行号、diff 快照、平台状态或 `updatedAt`；评论行号漂移或平台状态变化不会让决策失效。

`artifactPath` 只用于定位产物，不是授权身份。授权由 `reviewKey + findingId + proposalFingerprint` 匹配；同一份 artifact 移动或复制后仍然有效，路径相同但内容被替换时由指纹识别。

## 3. `review.json`

### 3.1 顶层

```json
{
  "schemaVersion": 1,
  "reviewKey": "acme/webapp#42187",
  "artifactPath": "/path/to/worktree/.engineering/work/ai-review/acme__webapp__42187__a1b2c3d4/review.json",
  "generatedAt": "2026-10-21T10:00:00+08:00",
  "repo": "acme/webapp",
  "mergeRequestId": 42187,
  "iid": 712,
  "mrUrl": "https://gitlab.example.com/acme/webapp/-/merge_requests/712",
  "sourceBranch": "feat/course-center-daily-iteration",
  "targetBranch": "master",
  "reviewHead": "a1b2c3d4...",
  "worktreeHead": "a1b2c3d4...",
  "headMatches": true,
  "selection": {
    "mode": "all",
    "requestedIds": []
  },
  "preflight": {
    "repo": "acme/webapp",
    "id": 42187,
    "iid": 712,
    "worktree": "/path/to/worktree",
    "sourceBranch": "feat/course-center-daily-iteration",
    "targetBranch": "master",
    "head": "a1b2c3d4...",
    "branch": "feat/course-center-daily-iteration",
    "branchMatchesSource": true,
    "dirty": false,
    "dirtyFiles": []
  },
  "summary": {
    "total": 19,
    "active": 0,
    "closed": 19,
    "platform": {
      "states": {"pending": 0, "handled": 19},
      "interpretations": {"CLOSED_NOT_ADOPTED": 19}
    }
  },
  "findings": [],
  "closedFindings": [
    {
      "id": 904201,
      "source": {
        "note": "...",
        "path": "src/...",
        "platformInterpretation": "CLOSED_NOT_ADOPTED"
      }
    }
  ]
}
```

`mrUrl` 优先使用平台返回的 MR `webUrl`；如果平台只给项目首页，则用 `repo + iid`
构造；默认主机取自 `GITLAB_HOST`（缺省 `gitlab.com`），SSH remote 主机与 web 主机不同时用 `--base-url` 显式指定。

`headMatches` 是聚合信号，不是执行准入：

- `true`：评论 context 与当前 worktree HEAD 一致。
- `false`：至少一条不一致；HTML 显示警告，执行前核对证据。
- `null`：无法比较（没有 worktree HEAD 或评论没有 context）。

`selection.mode=ids` 表示这是 `--ids` 试点子集，`requestedIds` 是试点 ID；HTML 会提示“不是全部 AI 评论”，不能把局部结果当成全量评审。

`preflight.dirty` 为 `true / false / null`：`null` 表示无法判断（例如 worktree 不是 git 仓库）；不要把它当成“干净”。`preflight.branchMatchesSource` 同样是预检事实，不是硬门禁：`false` 只提示当前分支与 MR `sourceBranch` 不同，执行前需要核对工作区，不能只凭分支名或提交号判断。

`findings` 包含本次要分析和决策的 active 评论；未选中的进 `closedFindings`，只有 `source`，没有 `analysis` / `proposalFingerprint`，也不进入 Decision Envelope。默认只把 `pending` 纳入 active，这是**目标缺省而非能力限制**：重分析任意状态（含已忽略 / 已处理 / 已合并）用 `artifact --state all`（或 `--state ignored/closed/handled`），`--include-closed` 为 `--state all` 别名。`findings=[]` 时 `closedFindings` 必须非空；HTML 仍可生成只读汇报页。

### 3.2 Finding source

`source` 是平台事实，不由 HTML 或 Agent 改写。`category / severity /
severityLabel / title` 由脚本从 badge 解析，模型不需要再解析评论首行。

```json
{
  "note": "![缺陷 · 中](...)\n\n...",
  "category": "缺陷",
  "severity": "medium",
  "severityLabel": "中",
  "title": "`foo` 可能为空",
  "path": "src/.../fields.tsx",
  "line": 46,
  "lineRange": {"fromLine": 46, "toLine": 46},
  "side": "new",
  "context": "old new",
  "oldSha": "...",
  "newSha": "...",
  "headMatches": true,
  "outdated": false,
  "platformState": "handled",
  "platform": {"adopted": 0, "closed": 1},
  "platformInterpretation": "CLOSED_NOT_ADOPTED",
  "suggestion": null,
  "diffContext": "@@ ...",
  "author": "codereview-copilot",
  "createdAt": "2026-10-20T10:00:00",
  "updatedAt": "2026-10-21T09:30:00"
}
```

`platformInterpretation` 的确定性映射（`platform_interpretation` 为唯一源，CLI / Artifact / HTML 都消费它）：

| adopted | closed | 值 | 含义 |
|---|---|---|---|
| 1 | 0 | `PENDING` | 平台待处理 |
| 0 | 1 | `CLOSED_NOT_ADOPTED` | 已关闭但未采纳，不等于已修复 |
| 3 | 1 | `IGNORED` | 已忽略（目标平台单 MR 观测；≠误报≠已修复，也不推断批量） |
| 2 / 4 等其他 closed=1 | 1 | `CLOSED_WITH_ACTION` | 已关闭且有动作，具体取值未观测，不猜 |
| 其他 | - | `UNKNOWN` | 无法判断 |

### 3.3 Finding analysis

```json
{
  "issueRisk": "medium",
  "assessment": "CONFIRMED",
  "recommendation": "FIX",
  "trigger": "输入框失焦时值为空",
  "impact": "提交空值或触发异常",
  "rootCause": "回退逻辑覆盖了空值",
  "evidence": [
    {"kind": "OBSERVED", "ref": "src/.../CourseForm.tsx:100", "summary": "..."}
  ],
  "openQuestions": [],
  "proposal": {
    "summary": "修正空值回退",
    "approach": "在 owner 中保留空值判断，不覆盖调用方输入",
    "files": ["src/.../fields.tsx"],
    "owner": "CourseForm",
    "changes": ["调整回退条件", "补回归测试"],
    "verification": ["npm test -- course-form"],
    "scope": "local",
    "fixRisk": "medium",
    "requiresHumanAcceptance": false,
    "alternatives": []
  }
}
```

### 方案语义 vs 实际补丁

- `source.diffContext`：MR 已发生的原始变更（事实）。
- `source.suggestion`：云端评论作者给的建议，不代表已应用。
- `analysis.proposal` 描述**修复意图与技术方案**（summary / approach / changes / files / verification），供人审批；不要求、也不默认展示 Agent 预生成的拟修改 Diff——精确补丁留给 Coding Agent 边写边调。
- `proposal.changes` 表述预期的实现调整，`proposal.files` 表述预期影响文件，**都不是具体补丁，也不是实施文件白名单**。
- 方案语义由 `proposalFingerprint` 覆盖：approach / files / changes 等实质变化 → 旧授权自动 stale。
- 实施后的真实 Git Diff 由 Coding Agent 输出（限定本次变更基线），用于验证是否符合已授权方案；正常实施无需再次人工批准，仅实质性偏离（如动到用户禁止的公共 API）才回退重决策。

Enums：

| 字段 | 值 |
|---|---|
| `assessment` | `CONFIRMED` / `DISMISSED` / `NEEDS_EVIDENCE` |
| `recommendation` | `FIX` / `DISMISS` / `DEFER` / `NEEDS_EVIDENCE` |
| `issueRisk` / `proposal.fixRisk` | `high` / `medium` / `low` |
| `evidence[].kind` | `OBSERVED` / `DERIVED` / `INFERRED` |

`analysis.issueRisk` 只描述问题本身的影响、触发概率与范围；`proposal.fixRisk` 只描述修复动作的契约影响、跨 owner 程度、可逆性与验证难度。两者不是同一个风险，不要互相替代。分档锚点见 `SKILL.md` 的「本地风险分档」。

约束：

- `CONFIRMED` → `FIX` 或 `DEFER`；`FIX` 必须有 `proposal.approach/files/verification`。
- `DISMISSED` → `DISMISS`，必须有反证；`proposal` 可以为 `null`。
- `NEEDS_EVIDENCE` → `NEEDS_EVIDENCE`，`openQuestions` 不能为空。它不授权修复；向云端补证用 `reply`，该条保持 `UNDECIDED`（尚无有效授权），不引入人工 `DEFER`。
- `FIXED` 不是修前值；执行后才能写 `IMPLEMENTED` / `FIXED`。
- `proposalFingerprint` 必须与当前 `analysis` 一致，Builder 会重新计算并拒绝不一致的 artifact。

### 3.4 模型写入：patch 命令

不要让模型重写整份 `review.json`。模型只产出一个小 patch，由脚本校验、写入并重算指纹：

```json
{
  "schemaVersion": 1,
  "reviewKey": "acme/webapp#42187",
  "findings": [
    {
      "id": 904201,
      "set": {
        "assessment": "CONFIRMED",
        "recommendation": "FIX",
        "issueRisk": "medium",
        "trigger": "输入框失焦时值为空",
        "impact": "提交空值或触发异常",
        "rootCause": "回退逻辑覆盖了空值",
        "evidence": [
          {"kind": "OBSERVED", "ref": "src/.../CourseForm.tsx:100", "summary": "..."}
        ],
        "openQuestions": [],
        "proposal": {
          "summary": "修正空值回退",
          "approach": "在 owner 中保留空值判断",
          "files": ["src/.../fields.tsx"],
          "owner": "CourseForm",
          "changes": ["调整回退条件", "补回归测试"],
          "verification": ["npm test -- course-form"],
          "scope": "local",
          "fixRisk": "medium",
          "requiresHumanAcceptance": false,
          "alternatives": []
        }
      }
    },
    {
      "id": 904202,
      "set": {"proposal.summary": "改为在公共组件内统一处理"}
    }
  ]
}
```

```bash
python3 <本 Skill 所在目录>/scripts/review.py patch \
  --artifact .engineering/work/ai-review/<slug>/review.json \
  --patch .engineering/work/ai-review/<slug>/analysis-patch.json
```

规则：

- `set` 的键相对 `finding.analysis`；支持 `proposal.summary` 这类点路径。
- `evidence` / `openQuestions` 是数组，必须整体替换。
- 默认要求被修改的 Finding analysis 完整；只写部分字段时显式加 `--allow-incomplete`，但 `review_html` 仍会拒绝不完整的 artifact。
- 脚本重算 `proposalFingerprint`，校验失败时不写入；先加 `--dry-run` 可预览。
- **禁止** patch 修改 `source`、`id`、`reviewKey`、`proposalFingerprint`，以及 `decision / status / note`。人工决策只在 `review.html` 中维护，不写回 `review.json`。
- `recommendation` 是 AI 的修前建议（`FIX / DISMISS / DEFER / NEEDS_EVIDENCE`），不是人工的 `APPROVE / CLOSE / DEFER / PROVIDE_INFO / UNDECIDED`。

### 3.5 并行分析

finding 之间默认没有分析顺序依赖。可以按 finding 或小批次并行分析：

- 每个 worker 只读取自己负责的 finding 的 `source` 与相关代码，返回一个 patch fragment；
- worker 只读代码，不修改工作区、不提交、不写平台；
- fragment 与普通 patch 同格式，只包含自己负责的 `findings[]`；
- worker **不直接写** `review.json`、不生成 HTML、不读写 LocalStorage；
- 主 Agent 合并 fragment 后用一次 `patch` 写入；可重复传 `--patch`：
  ```bash
  python3 <本 Skill 所在目录>/scripts/review.py patch \
    --artifact .engineering/work/ai-review/<slug>/review.json \
    --patch .engineering/work/ai-review/<slug>/analysis-a.json \
    --patch .engineering/work/ai-review/<slug>/analysis-b.json
  ```
- 跨 fragment 的重复 finding ID 会拒绝写入；同一个 finding 不能由两个 worker 各写一半。
- 只有同一根因 / 同一 owner 且一个 finding 的结论会改变另一个 finding 的前提时，才把这几条合并给同一个 worker；这不是全局串行规则。

## 4. Decision Envelope

Envelope 只包含 `findings` 的决策；`closedFindings` 不进入决策数组，也不需要人工决策。

`artifactPath` 只是定位信息，不参与授权匹配。授权身份是 `reviewKey + findingId + proposalFingerprint`；不要用绝对路径相等作为执行前提。

HTML 复制出的内容示例：

```json
{
  "schemaVersion": 1,
  "reviewKey": "acme/webapp#42187",
  "artifactPath": "/path/to/worktree/.engineering/work/ai-review/acme__webapp__42187__a1b2c3d4/review.json",
  "decisions": [
    {"findingId": 904201, "proposalFingerprint": "a1b2c3d4", "status": "APPROVE", "requiresHumanAcceptance": true},
    {"findingId": 904202, "proposalFingerprint": "e5f6a7b8", "status": "CLOSE", "note": "误报：该分支在生产不可达。"},
    {"findingId": 904203, "proposalFingerprint": "c9d0e1f2", "status": "CLOSE", "note": "本 MR 不处理，另单跟踪。"},
    {"findingId": 904204, "proposalFingerprint": "a3b4c5d6", "status": "UNDECIDED"},
    {"findingId": 904205, "proposalFingerprint": "b7c8d9e0", "status": "DEFER", "note": "本 MR 不处理，另单跟踪。"},
    {"findingId": 904206, "proposalFingerprint": "f1e2d3c4", "status": "PROVIDE_INFO", "note": "后端按白名单校验 category，三个疑问不成立。", "answers": {"0": "白名单在后端"}}
  ]
}
```

决策语义：

| status | 代码授权 | 说明 |
|---|---|---|
| `APPROVE` | 改代码 | 必须对应 `recommendation=FIX` 且 proposal 可执行；不代表已修复，也不自动 `adopt` |
| `CLOSE` | 不改代码，结束评论 | 必须有非空 `note` 理由；不代表平台已 `reject` / `ignore`，写回是反馈阶段单独确认 |
| `UNDECIDED` | 无动作 | 尚未处理，或被 stale / invalid 降级；不授权、不执行 |
| `DEFER` | 暂不处理 | 有效但非执行授权；本 MR 不处理、另单跟踪等 |
| `PROVIDE_INFO` | 提交补充信息 | 有效但非执行授权；需非空 `note` 或至少一个 `answers`；Agent 据此**重新评估整个 Finding**（问题假设、证据解释、结论与方案），不是机械填答案 |

`APPROVE` 另带 `requiresHumanAcceptance`，来自 `analysis.proposal.requiresHumanAcceptance` 的明确布尔判断。Agent 根据实际未覆盖的重要结果或用户要求决定，并在 `verification` 写明义务；风险高低和“人工 / manual”等词不自动产生人工验收。HTML 不做自然语言分类，仅展示并复制字段；check-envelope 拒绝与方案不一致或新方案缺失的验收值。判断改变会改变 proposalFingerprint，使旧授权失效。

兼容旧 artifact：缺该字段仍能读取；HTML 保守按需人工 / 补评展示。旧 Envelope 缺字段可恢复，但执行者必须补评，不能把缺省视为 false 或验证充分。新增 / 重评 FIX 方案应写明确布尔值。

Agent 消费规则：

1. 读取 `review.json`，校验 `reviewKey`；不要用 `artifactPath` 判断授权。
2. 运行 `review.py check-envelope`。输出把每条决策分成 `AUTHORIZED / STALE / INVALID`，并保留 `APPROVE / CLOSE / DEFER / PROVIDE_INFO / UNDECIDED` 计数；`DEFER` / `PROVIDE_INFO` 不计入 `AUTHORIZED`（非执行类）。
3. 只执行 `AUTHORIZED`（`APPROVE` 改代码、`CLOSE` 只结束评论）；`STALE` 只停该条，要求重新决策；`INVALID`（含 `CLOSE` 缺理由）也不执行。
4. `STALE` 不阻断其他 Finding；只有 envelope 级结构错误（`reviewKey` 不一致、decisions 非法等）才整体失败。
5. 执行前核对代码锚点、行为和证据是否仍适用；`headMatches=false` 或 `branchMatchesSource=false` 不是唯一准入，只是预检信号。
6. `requiresHumanAcceptance=true` → 自动验证通过后停下等人工验收，不标完成；`false` → AI 自验后完成，自验须说明验证覆盖了什么、结果如何、是否符合批准的修复方案（不是只跑命令）。
7. 验证失败或证据不足 → 不标完成，先修复或报告阻塞；实施需实质偏离授权方案 → 重新请求决策，不得先做未授权修改再事后补确认。
8. 平台反馈另行按用户要求处理，不从决策自动推导。

## 5. HTML 决策界面

- 数据通过 `<script type="application/json" id="review-data">` 嵌入；Builder 将
  `<`、`>`、`&` 替换为 JSON Unicode 转义，避免 `</script>` 破坏结构。
- 评论、diff、代码通过 `textContent` 渲染，不使用未转义的 `innerHTML`。
- 首屏展示：reviewKey、MR 链接、source/target branch、`headMatches` 警告、
  `branchMatchesSource` / `dirty` 预检提示、`CLOSED_NOT_ADOPTED` 数量、stale 数量、决策进度。
- 列表支持按决策、assessment、问题风险、路径/根因搜索；问题风险与修复风险分开展示。
- 列表操作列提供批准 / 退回重评 / 关闭快捷动作，均可撤销（写回 `UNDECIDED`，覆盖 AI 默认）；退回重评写 `PROVIDE_INFO`，非执行授权；「评估」不单独成列，由「AI 建议」唯一决定（契约 `ASSESSMENT_RECOMMENDATIONS` 保证无损）；「是否需要人工验收」列与 Envelope 的 `requiresHumanAcceptance` 同源字段、只读。
- 详情展示原始评论、云端代码建议（`source.suggestion`）、代码上下文、证据、根因、问题风险、方案、修复风险、验证要求、开放问题。
- `selection.mode=ids` 时显示试点范围提示，避免把局部试点当成全量评审。
- `closedFindings` 在独立区域只读展示；不进入决策、Envelope 或执行。
- 决策只存浏览器本地存储（LocalStorage）；顶栏「恢复 AI 默认决策」重置回 AI 默认（确认框展示将恢复为批准 / 关闭 / 未决策的条数，含被否决后重新获得授权的条数），「生成交接」弹窗内提供复制 Envelope 兜底；不提供 JSON 导出/导入。
- 浏览器本地存储不可用时显示警告，但查看和复制仍然可用。
- 不展示平台反馈控件；平台反馈是独立动作。

## 6. 失败与边界

- artifact 缺 analysis、枚举非法、指纹不一致：Builder 一次列出全部错误，不生成 HTML。
- 没有 AI 评论，或 `--ids` 没有匹配项：不生成 artifact。
- 目标 artifact 已包含 analysis：默认拒绝覆盖，保护已有分析；需要重新生成时用 `--out` 新路径，或显式 `--force` 丢弃旧分析。
- 全部评论 `closed=1`：默认只生成 `closedFindings` 汇报页，不要求 analysis；需要重分析时加 `--state all`（或 `--state ignored`）。
- 评论更新但 proposal 未变：决策继续有效。
- 单条 proposal 变化：只标该条 stale，HTML 要求重新确认，其他 Finding 仍可执行。
- 缺失 `proposalFingerprint` 的旧决策：保留供查看，但视为 stale，不授权。
- `APPROVE` 缺少有效 FIX 方案，或 `CLOSE` 缺少理由：check-envelope 标为 `INVALID`，只停该条。
- 全部评论 `CLOSED_NOT_ADOPTED`：默认只进入 `closedFindings` 汇报；需要分析 / 决策时加
  `--state all`，平台反馈仍需显式 `--include-handled`，且平台可能拒绝写入，失败要如实报告。
- `headMatches=false` 但证据仍适用：可以执行，但执行报告要说明版本差异。
- `headMatches=false` 且证据不适用：停该条，重新分析或重新决策。
