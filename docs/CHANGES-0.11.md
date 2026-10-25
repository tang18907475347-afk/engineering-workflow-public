# 0.11.0 变更说明

本版在 0.10.0 基础上有两项：重做 `ai-code-review` 的决策页视图层（D16），以及**新增一个独立 skill** `work-retrospective`（D17）。既有 Skill 的名称、边界与契约语义不变；Skill 数量由 8 个变为 9 个，新增的这个不接入 Router，只在用户明确要求时使用。

两条底线沿用 0.10.0：每个 Skill 能独立运行；不受模型强弱限制。

## 逐项说明

| # | 决定 | 改了哪些文件 | 回退方法 |
|---|---|---|---|
| D16 | `review.html` 视图层重做：明暗两套主题、手机宽度可用、顶部「交接预览」条（点色块即筛选）、详情页 ← → 切换、理由框自动聚焦与 ⌘/Ctrl+Enter 提交、交接前对未决策给出提醒；**不改**决策状态、Decision Envelope、`proposalFingerprint`、AI 默认决策与 localStorage 键；只用系统字体，不新增外部依赖 | `skills/ai-code-review/assets/review.html` | 用 0.9.0 / D14 的 `assets/review.html` 覆盖该文件即可（单文件模板，无其他依赖） |
| D17 | 新增 `work-retrospective`：按用户指定的范围（需求 / 任务 / 分支 / 任意时间段）对照请求与实际工作，找出走偏与走反，归因到用户侧 / agent 侧 / 插件侧 / 环境侧，结论分三条出口（对插件、对用户、对项目）；每条结论带证据指针与可信度档位；独立能力，不接入 Router，只在用户明确要求时使用；默认不写任何文件，用户在复盘后明确要求时可保存报告或按条写入 `.engineering/context.md`。会话采集不在本 skill 内，由用户或其 agent 按 `sources.md` 的事件格式提供；定位为一次性复盘，积累由用户决定，skill 不存档 | `skills/work-retrospective/`（新）、`scripts/sync_shared_references.py`（依赖一行）、`scripts/test_regressions.py`（skill 集合）、README / USER_PROMPTS 登记、`.qoder-plugin/plugin.json` 关键词 | 删除该目录，并撤回它在 `scripts/sync_shared_references.py`、`scripts/test_regressions.py`（skill 集合与两处数量）、README（两处）、USER_PROMPTS（两处）、`AGENTS.md`（skill 数量与 D17）、`.qoder-plugin/plugin.json`（关键词）中的登记 |

## 随 D17 吸收的独立审查意见
D17 提交后，另一个窗口按 `skill-architecture` 与 `skill-creator` 的标准做了静态审查，已吸收：文件写入边界统一为“默认不写任何文件”；隐私声明改成可验证的表述并加最小读取规则；证据词汇改用共享契约的 `OBSERVED / DERIVED / INFERRED`；“环境侧”不再混入数据缺失；档位与把握定义关系；`parent_id`、时区、路径等一致性问题；描述补自然说法与负例；出口 A 模板补备选方案；写不出反证的归因降为“推断”而不是直接放弃。

**未采纳**：现在不加采集脚本（两个平台的格式都没有官方规范、样本很少，等真实使用后再加，且应是可选加速器）；不新增存档目录（定位为一次性复盘，积累由用户决定）；不改 `plugin.json` 里的占位 URL，也不在描述和默认提示词里提复盘（与 `skill-architecture` 的处理一致）。

## 已经验证的（静态）
- `scripts/check_plugin.py --strict`：9 个 skill，0 ERROR、0 WARN。
- 回归测试 17 项、ai-code-review 82 项（1 项跳过）、implementation-strategy 8 项、product-engineering 5 项、product-design 14 项通过。
- D16：新模板在浏览器里验证过明暗主题、手机宽度、详情页与键盘切换；原 `ui_behavior_check.sh` 的 A/B/C 用例在页面内等价复现通过。**真实的 `ai-code-review/tests/ui_behavior_check.sh`（需要 playwright-cli）尚未在本机运行。**

## 还需要实测的（行为）
静态检查不证明模型行为变好。
1. **D17 `work-retrospective`（尚未实测）**：弱模型与最强模型各跑一遍——
   - 「复盘昨天下午定价页改版那轮，为什么改了三版」：是否触发；会话可读时片段是否合理；写入的文件数必须为 0。
   - 「复盘上个需求从澄清到提测，哪里走偏了」：只有项目产物、没有会话时，是否如实写“缺会话记录”，而不是编造用户意图。
   - 「复盘上个月」：是否先给一屏盘点并请用户收窄；没有数据时是否停止。
   - 负例「帮我总结这个 MR 改了什么」：不应触发。
   通过标准：没写任何文件；每条结论有证据指针和档位；缺数据有声明；推断没有被写成事实；三条出口各有产出或写“本次没有”；写不出反证的归因被降为“推断”而不是被大量改写成“无法判断”。**没跑完之前只能写“未实测”。**
