# intelligence 文档怎么组织
产物是 Agent 直接读写的 Markdown，中间没有任何机器格式。这里只讲组织方式。

## 文档骨架
```markdown
---
baseline: 5df4c21d1
scope: Template lifecycle
entrypoints:
  - 新建模板
  - 编辑模板
  - 模板卡 ⋯ → 编辑已关联模板
sources:
  - src/pages/projectTeam/components/TemplateEditorPage/index.tsx
  - src/pages/projectTeam/components/TemplateManageModal/service.ts
---

## src/pages/projectTeam/components/TemplateEditorPage/index.tsx

### handleSave
inputs: name / description / skillCategory / fileSource / cover
契约: 成功后不调 onClose，由宿主 onCreated / onSaved 收尾；提前关闭会丢成功态
create:
- calls → TemplateManageModal/service.ts#createTemplate search:const response = await createTemplate({
```

- `##` 是 **owner 节**，标题是目标仓库相对路径。这是刷新边界：文件变了就重建它持有的那一节。一份文档可以包含多个 owner 节。
- `###` 是一个值得被独立引用的事实，标题就是它的 anchor。
- front matter 四项的语义见 [intelligence-contract.md](intelligence-contract.md) 不变量 4；`baseline` 取 `git rev-parse --short HEAD`。同一源码文件允许出现在多份文档的 `sources` 里（shared 源码），多份文档 baseline 不一致也正常（各自刷新）。

## 三种表达，不混用
|表达|形式|承载|
|---|---|---|
|属性 / 契约|`key: value`|`inputs` / `mode` / `contract`（`契约:`）/ `validates` / 语义备注|
|关系 / 行为|`- verb → target search:<字面量>`|跨文件与跨层的语义边|
|业务分支|`create:` / `edit:` / `success:` / `failure:` 领起|分支下的内容仍用上面两种|

**同一个动词不能既当字段又当边**：写了 `- calls → foo` 就不要再写 `calls: foo`。关系一律用边语法，否则读者无法判断哪条是可遍历的关系。一行只放一条边和它的 locator，不并列两个 `search:`（边界无法切分）。

字段名按事实形态自取，不是固定枚举；同类短并列项压在一行（`inputs: name / description / skillCategory`）。字段里出现的名字仍必须能在 owner 文件里 grep 到——内联不是放宽证据，只是不单独建节。

## 关系动词
`contains` / `renders` / `triggers` / `calls` / `reads` / `writes` / `requests` / `navigates`。

跨文件委托（校验、格式化、编码转换、错误映射）就是 `calls`，指向真实 owner，契约写在那一节——不为它新造动词。副作用（存储 / native bridge / 埋点）也是 `calls` 的目标，于是新增一类副作用不需要新增枚举，遍历时天然停在副作用边界。

`contains` 只记有业务导航价值的边：跨组件 render / composition、page → key child surface、host → modal / editor / 全屏页。同文件的 local handler / state / button 不记——owner 节与小节层级已经表达了归属，再写一遍只是噪声。

`triggers` 另记 `event:`，取源码里真实存在的事件绑定（`onClick` → click、`onChange` → change）。locator 与 `event:` 可以来自不同位置：locator 要能连到具名 handler（隔着 prop 透传时解析到具名 handler 为止），`event:` 要的是真正的 DOM 事件。推不出绑定就不写这条边，也不要凭元素看起来像什么去填事件名。

## locator
优先级 **真实 symbol > 稳定语义搜索词**：

|情形|写法|
|---|---|
|函数 / 类 / hook / 组件 / 导出常量 / store action|anchor 直接写 symbol 名，不再重复 `symbol:`|
|route|anchor 写路由字面量（`/orders/create`）|
|API 端点|anchor 写 `<METHOD> <path>`，边上的 `search:` 给源码里原样出现的路径字面量——源码里并不存在 `POST /api/v1/agents` 这个整串，给了 Agent 就 grep 不到|
|state / store|anchor 写 `<store>.<key>`；无具名 setter 时 `search:` 给赋值语句字面量（`search:marketplaceState.teamTab = 'created'`），不要退回 `symbol:` 去猜一个不存在的 setter|
|UI 元素|anchor 写可见文案或 `data-testid` 值，紧跟一行 `search:` 给绑定字面量。只保留静态可证的语义属性（testId > aria-label > 文案 > placeholder > href），不合成 CSS 选择器|
|匿名节点|不承诺稳定 identity，把事实挂到最近的稳定 owner（命名组件 / action）上|

三条约束：

1. `search:` 的值必须是源码里原样出现的字面量，直接搜索就能命中，不需要推断。
2. locator 命中的必须都指向同一个东西；命中多个不同目标就换更具体的词（`search:'/api/v1/agents'` 会同时命中 `/api/v1/agents/types`，改用 `search:('/api/v1/agents', { ...params })`）。
3. 行号不进 intelligence，一次编辑就作废。

**跨文件引用的写法**：同文档内直接写 anchor（`handleSave`）、不加路径；跨文件按不变量 3 的最短唯一后缀，root 约定为 `src/`。

**跨文档不建 intelligence-to-intelligence 的边**：需要提到别的文档覆盖的事实时，直接给它的源码 locator——源码 locator 永远可 grep，因此既不会悬空，也不需要跨文档引用表。shared 实现细节不复制，只写它对当前链路的作用。

## 什么该独立成节
只有需要被独立引用 / 反向查询，或需要承载多条高价值事实的节点才建 `###`。纯叶子事实内联到最近的高价值节点：

```text
### createTemplate
- requests → POST /api/v1/me/skills/create search:'/api/v1/me/skills/create'
```

端点没有额外 consumers、契约或响应语义要讲时，就只留调用方的一条边，不建 API 小节。反过来，`marketplaceState.teamAgents` 这种被跨文件写入、是业务结果、反向查询「谁改了这份 state」需要它能被引用的，就保留独立节。两者差在删除测试的结果，不差在它属于哪一类节点。

## 分片与 overview
分片单位见 [intelligence-contract.md](intelligence-contract.md) 的「产物」段。本文件只回答「文档应该长成什么样」，不回答「什么时候拆 / 合」（那是改的时机，在 intelligence-contract.md）。判断当前分片好不好只看两个信号：

- **该拆**：回答一个问题通常要跳过文档中绝大多数内容；文档里包含多个几乎互不相关的业务入口；刷新一个小功能经常导致整份大文档重建。
- **拆过头**：同一个 Page / API / state 在多份文档里重复解释；一次 query 经常要打开很多小文件；改一个源码文件要同步重写大量文档。

每个大模块最多一份 `overview.md`，只写「有哪些文档 + 各自 `scope` 与 `entrypoints`」：

```markdown
# Project Team

- project-lifecycle.md — scope: 项目创建 / 编辑 / 提交；entrypoints: 新建项目、编辑项目、模板卡 ⋯ → 编辑已关联模板
- template-management.md — scope: 模板创建 / 编辑 / 上传；entrypoints: 新建模板、上传模板、md 编写 Skill
```

不复制正文，不建全仓二级摘要副本，也不维护「尚未纳入 A / B / C」这类无界清单——边界由各文档的 entrypoints 表达，缺口因此可判定。

## 不规定其余格式
不固定 section 名、不固定列、不强制表格。按数据形态选最自然的表达：owner 用标题，属性用紧凑字段，行为链用缩进和箭头，只有少数规则矩阵才用表格——缩进本身携带的层级信息，压进表格就没了。`/` 并列、`create:` 领起都只是书写惯例，Agent 直接读，不需要任何解析器。也不继续优化字符数：压缩的对象是展示包装，不是证据，为了把 create / edit / failure 写准而多出几行是合理的。

完整样例见 [worked-example.md](worked-example.md)。
