# 增：判断什么值得缓存
四条不变量与 CRUD 操作模型在 [intelligence-contract.md](intelligence-contract.md)。本文件只服务 **增**（以及增错了之后的 **删**）：怎么判断一个事实值不值得入库、owner 怎么定、契约与分支怎么抽。查 / 改 / 删 的时机与流程不在这里。

## 增：准入三道判断
落地时按顺序过三道（第一道就是不变量 1 的那一问），任一不过就不记：

1. **恢复成本**：一次 grep / symbol search / 单文件几行就能恢复 → 不记。需要跨多个文件、需要理解条件分支、需要总结时序或协议、局部阅读很容易得出错误结论 → 记。
2. **删除测试**：删掉它，后续 Agent 对业务行为的理解、定位能力或反向查询能力是否明显下降？否 → 内联为字段行，或不记。
3. **owner 可证**：这条事实在它的 owner 文件里 grep 得到证据吗？grep 不到就改成关系指向真实 owner（不变量 2），或留 `unresolved`。

三道都是判断，不是评分。特别地，graph degree 不是删除依据：一个只被一个调用方抵达的 API 可能正是链路终点。

## 增：契约怎么写
契约不是实现摘要。写清四件事：**实际语义、关键条件、与直觉不同之处、违反后的结果**。不强制字面出现「否则」，但必须表达实际后果。不要把普通赋值或函数调用包装成契约。

```text
# 不是契约：只是复述函数做了什么，防不住任何错误改动
templates 契约: template_ids 提交模板列表
版本契约: expectedVersion 映射 expected_version      # 补上「未传时整个字段不携带」才成为契约

# 是契约
resetRequest            → 有已有数据时不会重新请求（requestedRef 仅在 createDefaults 为空时复位）
loadCategoryCode   → 入参是分类文案、返回编码；失败静默返回 undefined，不抛异常
edit template_ids          → 始终发送；[] 表示清空；省略表示不生效
handleSave success      → 不直接 onClose，由宿主 callback 收尾；提前关闭会丢失成功态
```

判断标准：**这条契约能不能防止一个具体的错误改动？** 能 → 写；不能 → 不写。契约允许用一句高密度自然语言完整承载，不要为了结构化把它拆碎。

契约本体写在**定义它的那个文件**的节里，调用方只留一条 `- calls →`（不变量 2）。同一个动词在不同 owner 下语义可以相反——`TemplateEditorPage.handleSave` 成功后不调 `onClose`，`ProjectCreateEditPage.handleSubmit` 成功后必须调 `onClose`；把其中一条抄到另一个 owner，就同时制造了归属错误和事实错误。

## 增：关键副作用 action 的分支
对 save / submit / create / update / publish / delete / upload 这类关键行为：

> 如果不同分支具有不同业务语义，并且这些差异需要较高阅读成本才能恢复，就必须保留分支。

```text
create:
- calls → contentMarket/services/marketplace.ts#createMyProject search:const response = await createMyProject({
- template_ids 非空才携带 search:...(templateIds.length ? { template_ids: templateIds } : {})

edit:
- calls → contentMarket/services/marketplace.ts#updateMyProject search:const response = await updateMyProject({
- template_ids 始终携带；[] = 清空，省略 = 不生效 search:template_ids: templateIds,

success:
- 创建走 onCreated、编辑走 onSaved，随后必须 onClose，否则与宿主预览面板叠层 search:onCreated?.(savedProjectIdRef.current)

failure:
- create 的 code=1018 安审拒绝：msg 入底部错误条 + 全量 toast + 按关键词标红字段并滚动定位 search:/审核|安审/.test(message)
- 网络层错误（TypeError / failed to fetch）映射为「网络异常，请检查网络后重试」search:isNetworkError
```

整段都在 `ProjectCreateEditPage/index.tsx` 这**一个** owner 节里；端点本身的 `- requests →` 边归 `contentMarket/services/marketplace.ts`。分支不是可以跟 owner 混摆的排版单位。

只有多个分支业务语义完全一致时才能合并。这不是为了 branch coverage，而是避免把真正昂贵的信息压掉。

失败终点记的是**用户能感知到、业务行为不同的结果**：主要 success result、关键失败出口、特殊业务错误码、version conflict、用户可见的 error state / toast / error bar。不是完整异常控制流，不是「try/catch 每条路径全记录」。当前 bounded scan 没追失败链路，就按不变量 4 显式写 `[failure path not captured]`，让「确认没有特殊失败逻辑」与「当前没采」可区分。

## 增 / 删：调用方列表不缓存
shared hook / service 的 callers 列表默认不记（不变量 1 + 2）。两种写法都不要：

```text
# 不记：证据在别的文件，改按 owner 重建时永远轮不到它
### useTemplateManageDialogs
used by: AccountMenu / ProjectPromptBox / ChatComposer

# 也不记「怎么搜」——如何搜索同样是廉价事实，不需要长期缓存
used by: search:useTemplateManageDialogs(
```

只有某个消费者关系本身携带高价值业务语义时，才由**消费者 owner** 自己记一条出边：

```text
## src/pages/projectTeam/components/ProjectCreateEditPage/index.tsx
### handleEditMountedTemplate
- calls → template-manage/useTemplateManageDialogs.ts#loadCategoryCode search:await loadCategoryCode(
```

这条边同时回答了「谁在用」——它由调用方持有，调用方变了它就被重建，不会 stale。

## 增：bounded scan 的取舍
扫描停止条件见 [intelligence-contract.md](intelligence-contract.md) 的「增」。这里只补一条最容易越界的：

**读过一个 source file ≠ 完整抽取该文件的所有事实。** `service.ts` 在 `sources` 里而它同时导出 list / detail / publish / delete，当前 `scope` 只关心创建与编辑，那么 publish 不在这份文档里——这只说明它不在 scope 内。不要用 glob 概括没逐个读过的目录，也不要为了「文件已在 sources 里」去补全它的所有导出。

## 增：缺口怎么表述
缺口的表述本身也要能核验（不变量 3）：除非已确认定义不在当前 `sources` 且确实没读过它，否则不要写「未扫」「不存在」这类元判断——宁可写 `request endpoint: unresolved`，或直接不下结论。**缺信息可以接受，错误解释「为何缺」不可以。**

同理，**缺边优于假边**：缺一条只是让 Task Context 少一跳，用户可以追问；假边会让整条链的结论都不可信，而且没人会去怀疑它。

## 推导示范（不是规则清单）
下面每行都是从四条不变量直接落下来的判断，用来示范推导方式。**新 case 一律回到不变量推导，不要往这里追加条目。**

|判断|由哪条不变量落下来|
|---|---|
|`submitting` / `loading` 不记|1 —— grep 一次即得，不昂贵|
|`contains` 大量省略|1 —— 一次局部源码即可恢复|
|callers 列表不缓存|1（symbol search 可恢复）+ 2（证据在消费者 owner）|
|validation 契约归 validation.ts|2 —— owner 闭合|
|create / edit 的 `template_ids` 必须拆开|1 —— 昂贵的协议差异不能被压掉|
|version conflict 必须记录|1 —— 高业务风险、用户可观察的昂贵事实|
|行号不作为核心 locator|3 —— 必须可重新核验|
|「没有记录 ≠ 不存在」|4 —— 不制造完整性幻觉|

## 增 / 改：交付前自检
一次过完，发现一处改一处（逐条返工会把整套规则反复重读）：

- 每节内的取值 / 契约 / locator / 分支条件都能在**该节对应 symbol 的函数体内** grep 到——同文件命中不算（`saveProject` 节里不能放 `handleSubmit` 的 `onClose`）；grep 不到的已改成 `- calls →` 指向真实 owner，契约本体已写进真实 owner 的节，且那个文件已加进 `sources`。
- 每条事实都带可重新搜索的 symbol 或 `search:` 字面量；`search:` 的值在源码里原样出现，且命中的都指向同一个东西（`currentOrder:` 会同时命中声明和写入，就换成 `set({ currentOrder: order })`）。跨文件引用是最短唯一后缀，有歧义已逐级扩大。
- 契约写出了语义差异或违反后果，不是实现摘要；协议不同的分支已拆开；关键副作用 action 有可观察终点，没追失败链路的已写 `[failure path not captured]`。
- 事实的语言强度没有超过源码证据；解析不动的关系留 `unresolved` 或干脆不写，没有猜的边。
- 独立小节只给了值得独立引用的节点：纯 API 叶子、只服务当前 action 的局部 state、内部展示 UI 都已内联成字段行或一条边；没有为覆盖 kind / relation 词表而存在的节点，也没有 cached callers。
- front matter 的 `scope` / `entrypoints` / `sources` / `baseline` 都已更新；没把「没记录」解释成「不存在」。
- 本文档只承载一个业务上内聚的 cluster：出现多个互不相关的业务入口就拆，出现与其他文档重复解释同一 Page / API / state 就合。

形状合法不等于值得存在——形状完美的噪声小节同样是膨胀，判据回到开头的三道判断。
