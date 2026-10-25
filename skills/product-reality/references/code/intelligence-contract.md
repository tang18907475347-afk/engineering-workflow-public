# Code Mechanism Intelligence Contract
> **代码机制缓存是高成本代码事实的缓存。**
> 本节教 Agent 对高成本代码事实做**增、删、改、查**，让新的 Agent 窗口能复用已有业务理解，同时避免陈旧或误导的事实长期存在。

**它是工程机制知识基础设施，不是产品事实或产品决定的权威。** `.engineering/product/` 记录 Current Reality，`.engineering/design/` 记录目标设计与已接受决定；代码机制缓存只回答「代码现在如何实现」。两者冲突时，按各自合同记录并回到源码/原始来源核验，不用缓存覆盖产品事实，也不用产品文档覆盖当前源码。缓存不参与决定状态、handoff 或 TRR 裁决。

缓存对象：需要跨文件阅读、较高业务推理成本、容易被局部阅读误解，并且后续 Agent 很可能重复需要的代码事实。它不是完整 Semantic Graph、全量代码索引、AST 摘要、API / state / component 清单、完整 Flow 数据库，也不是 completeness system。它是缓存，**不是必须同步维护的第二套数据库**。

**设计优先级：命中可信度 > 覆盖率。** 这个模型只有两类失败：

- **`cache miss`** —— 没记录，Agent 回源码重新搜索和推理。成本较高，但会自然暴露、可恢复，**可以接受**。
- **`stale / misleading hit`** —— intelligence 中已有事实，但事实错误、陈旧、归属错误或给出虚假的完整感。Agent 直接相信并做错误业务决策，不容易自我暴露，**是最高风险**。

一切取舍由此推导：**宁可 miss，不可误导。**

产物只有一层派生：目标仓库根目录下的 `.engineering/intelligence/<业务模块>/<cluster>.md`（每份覆盖一个业务上内聚的局部上下文，文档内按源码文件分节，一份可含多个 owner 节；分片单位是 **Agent 的有效读取窗口**——回答一个问题通常只读 1~3 份，改一个源码文件只刷新少量文档），以及回答时现组织、用完即弃、不写回文件的 **Task Context**。源码是唯一事实来源，`.engineering/intelligence/` 可整目录删除重建；项目根 `.gitignore` 统一忽略 `.engineering/`；不代为提交、不清理既有目录。

**用**：一个需求涉及哪些入口与接口、某个用户入口点下去会发生什么、改动影响面、可自动化验证的操作点与可断言结果、代码改完后刷新缓存。**不用**：一次 grep / symbol search / 读单文件局部就能答的问题；纯样式或纯文案改动。用户不会先知道 `.engineering/intelligence/` 存在——「这个需求要改哪些地方」就是在请求一次查。

## Requirement Context 作为探索种子
调用方提供 PRD、Design 或 Clarification，且需要理解本需求相关的高成本跨文件 Current Repo behavior 时，可以把 Requirement Context 用作**探索种子**：

```text
Requirement Context → 决定值得找哪些事实
Current Repo → 证明当前什么是真的
代码机制缓存 → 只记录通过既有门槛的派生事实
```

- 只从上下文提取业务概念、行为、状态、边界和待核验问题来缩小范围；Requirement terms 是 discovery hints，不是 Current Repo evidence，也不能直接写成 intelligence fact。
- 先查已有 intelligence；hit 不足、miss 或 stale 时回 Current Repo 做 bounded exploration，直到当前问题闭合即停。Current Repo 始终是事实权威。
- 只探索真正影响当前需求理解、且符合缓存现有高成本 / 跨文件准入的问题；简单 grep、symbol、单文件、已有明确 owner 或需求自身即可回答的问题直接查源码。
- 写入门槛、freshness、owner / source 闭合、可重新核验和 miss / stale / zero-write 语义完全沿用下方既有规则。没有值得缓存的事实时，完成当前任务并 zero-write 是成功结果。
- 这不是新的 mode、workflow 或 artifact，也不触发全仓扫描、完整领域建模、mandatory preload 或 mandatory cache write；不把 Product decision、Implementation plan、change boundary 或 API / state 方案写入缓存。

# 四条不变量

## 1 · 只缓存昂贵事实
判断只问一句：**如果没有这条 intelligence，Agent 恢复它需要多少源码阅读和业务推理？**

优先缓存：跨文件行为链、协议字段差异、create / edit 等分支语义差异、时序要求、callback ownership、特殊失败结果、反默认假设、很容易被函数名或字段名误导的真实行为、修改错误会造成明显业务 bug 的约束、需要读几十到几百行才能稳定总结的业务规则。

默认不缓存：`submitting` / `loading` / `saving`、普通 modal boolean、普通 `contains`、单纯 component hierarchy、一次 symbol search 即可恢复的调用方列表、普通 API wrapper 字段映射、纯展示 UI、一眼能从函数名或 JSX 恢复的结构事实、单纯为了覆盖 kind / relation 词表的节点。不新增 importance score、ranking 或 taxonomy。

## 2 · 事实与 owner 必须闭合
每条缓存事实只能存在于**能够直接提供其源码证据的 owner / source** 下，使得：**未来这个 owner 变化时，改必须能够触达并重建这条事实。** 归属错的事实永远不会被重建——它会持续提供一个看起来可信、实际已过期的结论，正是最危险的 `stale hit`。

**闭合到 section 粒度，不只到 file 粒度**：`search:` 在同一个文件里命中，并不代表它能证明当前 section——证据必须落在这一节对应的那个 symbol 体内。这是 locator 最容易给的假安全感：`saveProject` 节里写 `search:onCreated?.(...)` 能通过文件级 grep，但那行代码实际在 `handleSubmit` 里。

禁止：A 文件 section 抄 B 文件定义的契约；shared hook 节缓存多个消费者文件里的 callers 结果；把跨文件推导出的事实伪装成本地事实。正确：当前 owner 内只记录自己能证明的事实，跨文件语义使用关系（`- calls → other/file.ts#symbol`），真正的业务契约放在真实 owner 里。

```text
错：ProjectCreateEditPage 节 → 契约: 系统提示词 50-1000 字      # 规则真正定义于 project-profile-constraints.ts
对：ProjectCreateEditPage 节 → - calls → project-profile-constraints.ts#getProjectPromptValidationMessage
    project-profile-constraints.ts 节 → 契约: trim 后 50-1000 字；全空白与真空分开提示；返回 undefined 表示通过
```

owner 就是「证据写在哪个文件的哪个 symbol 里」这一个判断，不新增 owner graph 或 dependency database。

## 3 · 每条缓存事实必须可重新核验
代码机制缓存不是模型记忆，每条高价值事实都必须能让后续 Agent 回到源码重新验证。locator 优先 `file + symbol`，其次 `file + semantic search locator`（源码里原样出现、可直接 grep 的字面量）。

跨文件引用使用**相对 repo root 的最短唯一后缀**：`TemplateManageModal/service.ts#createTemplate`；不唯一就逐步扩大路径，直到唯一。不依赖行号作为 identity、AST path、structural hash、fingerprint、历史 node id，也没有 reconciliation engine。**事实的语言强度不能超过源码证据**：源码只能证明「可能」，就不要写成「必然」。

## 4 · 不制造完整性幻觉
代码机制缓存是 selective context，不是 completeness index。每份文档在 front matter 声明四项：

```yaml
baseline: 5df4c21d1 # git rev-parse --short HEAD
scope: Template lifecycle # 业务主题
entrypoints: [新建模板, 编辑模板, 上传模板, Markdown 编写 Skill] # 本次 bounded scan 实际围绕哪些用户入口展开
sources: [src/pages/projectTeam/components/TemplateEditorPage/index.tsx] # 实际读取过哪些源码，provenance / freshness 依据
```

必须明确：`sources` 不代表文件已完整抽取，`entrypoints` 不代表页面没有其他入口，**intelligence 没写某事实 ≠ 仓库不存在该事实**——查不到就回源码搜索，不做负向存在性判断。关键行为链如果某个重要分支没有追到，显式暴露 `[failure path not captured]`。不新增 completeness score、coverage percentage、per-file scanned status、negative index、scanned anchor registry。

# CRUD workflow
每次处理代码机制缓存，先判断是**查、增、改还是删**；CRUD 只是四条不变量的操作化，不是新的规则体系。已有 intelligence 足够就进入任务；查不到时回源码，只有发现昂贵事实才增；命中 stale 或错误事实时先改 / 删再继续。不要全量刷新、补齐所有缺口或每次任务结束都强制写入。

## 查
目标是用最少上下文获得足够可信的业务理解，而不是重新核验整份 intelligence。

1. 简单 grep / symbol lookup 可回答的问题直接查源码；跨文件行为、协议、时序、失败分支、业务影响面或 Web 自动化操作点与断言结果优先查 intelligence。
2. 按 `scope` / `entrypoints` 选最相关的 1–3 份文档，从语义锚点沿相关关系遍历，到问题闭合即停，不加载整个 `.engineering/intelligence`。
3. intelligence 只提供正向已知事实：查不到就回源码，不能由“没写”推出“不存在”；只核验当前决策真正依赖的 facts。

> **缓存用来决定该读哪里；源码用来确认当前决策真正依赖的事实。**

回答记法：缩进 + `→`，每行一个事实、自带文件路径与 locator，不用表格（缩进本身就是信息）、不输出行号。`create:` / `edit:` / `success:` / `failure:` 分支标签在问题涉及分支差异时必须带出来，不能拼成一条看似统一的链路；success 与 failure 终点一起给；写着 `[failure path not captured]` 就如实转述，不沉默也不推测一个看起来合理的失败行为。

## 增
增只沉淀恢复成本高、需要跨文件推理、容易被局部代码误导、后续可能复用且改错会造成真实业务风险的事实；廉价事实保持 cache miss。证据写在哪个 owner，就进入哪个 owner 节；契约与分支准入见 [extraction.md](extraction.md)。bounded scan 以当前问题语义闭合为停止条件，读过的文件写入对应 `sources`。

## 改
改只在 source 变化、事实被核验为 stale / 错误或业务语义变化时触发。根据 `sources` 定位受影响文档，重新读取当前源码并重写相关 section，清理悬空引用、更新 baseline / sources；拿不到 Git 或 baseline 时明确新鲜度未知并回源码核验；不在旧结论上追加 patch，不全量刷新，也不把 Git history 当 authority。

## 删
删应移除已不存在、被新语义替代、当前核验错误、无法由 owner 证明、已廉价化或重复的事实，只保留真实 owner 的版本；不写 tombstone 或 deletion log。宁可 cache miss，也不要保留可能误导的 stale hit。

# Cold start
`.engineering/intelligence/` 不存在或没有相关文档时，本质就是**先查、查不到再按需增**，不是全仓扫描：

```text
用户问题 → 查：找入口（路由 / UI 文案 / API 名 / 已知 symbol），确认没有可用 intelligence
        → 回源码完成任务：bounded scan 只扫入口所在文件及其直接依赖，沿高价值关系向外扩，够答即停
        → 增：只把过了入库门槛的昂贵事实写进对应业务模块文档，读过的文件写进 sources
```

`full bootstrap` 只在用户明确要求时执行（初始化仓库 intelligence / 建立完整索引 / 全仓扫描）：先识别骨架（技术栈、路由机制、请求封装、状态层、真实源码根目录），再按业务模块分批扫，不要试图一次通读整个仓库；分批产出按分片规则落到各业务模块文档，不默认堆进单一 `context.md`。

遇到新情况先回到四条不变量推导，**不要往 references 里追加「禁止 XXX」条目，也不要新增第五套规则或任何生命周期基础设施**。
