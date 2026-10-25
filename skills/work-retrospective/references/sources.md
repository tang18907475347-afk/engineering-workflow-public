# 证据来源与事件契约
> 本 skill 不绑定任何平台。接入方（执行采集的 agent 或脚本）把各平台的会话记录转成下面这种统一的事件流，本 skill 只读这种事件流。采集与转换由接入方负责。

## 为什么要有一份契约
各平台的会话记录格式不同、没有官方规范、会随版本变化。让分析逻辑直接读各家格式，每换一个平台、每升一次版本就要改。把差异收在接入层，分析层才能稳定。

## 统一事件
每个事件一行，字段如下；没有的字段可以缺省，不要伪造。

```text
ts          时间（UTC，ISO 8601）
source      来源平台，如 codex / workbuddy
session_id  会话标识
event_id    事件标识（会话内唯一）
parent_id   上一个事件（平台提供时才有；没有就不写，不要猜）
actor       user | agent | tool | system
kind        message | reasoning | tool_call | tool_result | interrupt | approval
            | file_change | commit | meta | unknown
text        文本（用户或 agent 的发言），可以是指向原文的指针
tool_name   工具名（tool_call / tool_result）
call_id     工具调用的配对标识
cwd         工作目录
model       模型名
raw_ref     原始记录的文件与行号，便于回到原处核对
```

## 读取原则
1. **读时解释。** 遇到不认识的记录类型，保留为 `kind: unknown` 并带上 `raw_ref`，不要丢弃，也不要猜它的含义。
2. **缺失就是缺失。** 平台没有记录的信号（例如没有“中断”事件），报告里写“该来源无此信号”，不要从沉默里推出“没有发生”。
3. **格式会变。** 以下观察来自第三方文章与本机抽样，不是官方规范。接入方应先探测本机的实际格式，再据此转换。

## 已观察到的格式（非官方，可能已变化）

### Codex
- 位置：`~/.codex/sessions/年/月/日/rollout-*.jsonl`，较旧的会被压缩成 `.jsonl.zst`；旁边有 `state.sqlite` 做索引。
- 每行三个字段：`timestamp`、`type`、`payload`。`type` 有 `session_meta`（会话 id、工作目录、提交）、`turn_context`（模型、审批策略、沙箱）、`response_item`（消息、函数调用与输出，按 `call_id` 配对）、`event_msg`（用户消息、agent 消息、patch 应用、命令结束等）、`compacted`。
- 能提供：用户请求、命令失败、重复重试、patch、模型切换、耗时。
- 待确认：用户中断与审批拒绝是否被记录，现有资料没有写明。命令输出会被截断，默认只持久化一部分事件。
- 因果：没有显式的父子引用，并行工具调用只能靠时间顺序推断。

### WorkBuddy
- 位置：`~/.workbuddy/projects/<工作目录名>/<会话 id>.jsonl`；执行轨迹在 `~/.workbuddy/traces/`。
- 会话每行带 `type`、`timestamp`、`id`、`parentId`、`sessionId`、`cwd`。`type` 有 `message`（含 `role` 为 user 或 assistant）、`reasoning`、`function_call` 与 `function_call_result`（按 `callId` 配对）、`session-meta`、`ai-title`、`file-history-snapshot`。
- 能提供：用户与 agent 的每一轮、工具调用与结果、**`parentId` 构成的因果链**、所用模型。
- 轨迹：类似链路追踪，含调用的起止、耗时、工具名、输入输出（可能被截断）、token 数，摘要里带当时的用户提示。
- 待确认：用户中断、审批拒绝、纠正在已有样本中没有对应的事件类型；样本量很小，不足以断言它没有。

### 版本历史与项目产物
- 版本历史：分支、提交、MR、回滚、合并之后针对同一处的修复。
- 项目产物：`requirements/<req>/` 下各 skill 的产物，`.engineering/context.md`。这些是结构化的，比会话记录更稳定，复盘应优先用它们还原“当时怎么理解的、定了什么”。

## 数据量与历史
会话记录可能很少，也可能已被平台清理。数据量不足时，复盘做定性分析，不做统计；报告里写明“样本只有 N 个片段”。越早把会话存档到本机，以后能复盘的历史就越长，采集是这件事里最不可补救的一环。
