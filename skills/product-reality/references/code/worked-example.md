# 真实案例：项目编辑页关联模板后保存
问题：

> 「在项目编辑页改一个已关联模板、再保存项目，会经过哪些代码？改提交逻辑要注意什么？」

这不是简单 lookup：链路跨多个 owner，create/edit 协议不同，模板保存与项目保存的关闭语义相反，版本冲突也不是错误码判断。

## 1. bounded scan
从两个入口出发，只读到足够回答为止：

* 模板卡 ⋯ → 编辑
* 项目编辑页「保存」

最终发现以下高价值事实。

### ProjectCreateEditPage/index.tsx
`handleEditMountedTemplate`

* 编辑入口仅对 `visibility !== 'public' && templateId` 的模板出现。
* `templateEditReqIdRef` 是竞态守卫；旧异步响应回来时 reqId 过期则整段丢弃。
* detail 返回分类展示文案，进入编辑器前调用 `loadCategoryCode` 转协议编码。
* calls → `getTemplateDetail`
* calls → `loadCategoryCode`
* navigates → `TemplateEditorPage(mode="edit")`

`handleSubmit`

* 调 `saveProject`，返回 false 就直接 return，不触发任何宿主回调。
* success: create → `onCreated`，edit → `onSaved`，随后**必须** `onClose()`；不关会与宿主打开的预览面板叠层。

`saveProject`

* create: `template_ids` 非空才携带。
* edit: `template_ids` 始终携带；`[]` = 清空，省略 = 不生效。
* 只返回 boolean 并写 `savedProjectIdRef`，**不碰任何宿主回调**。

```text
search:onClick: () => handleEditMountedTemplate(templateCard)
search:const saved = await saveProject()
search:onCreated?.(savedProjectIdRef.current)
search:...(templateIds.length ? { template_ids: templateIds } : {})
search:template_ids: templateIds,
```

`onCreated / onSaved / onClose` 的证据在 `handleSubmit` 体内，不在 `saveProject` 体内。**同文件命中不算闭合**：这条契约只能写在 `handleSubmit` 节，写进 `saveProject` 节会同时骗过文件级 grep 和读的人。

### template-manage/useTemplateManageDialogs.ts
`loadCategoryCode`

* 输入分类展示文案，输出协议编码。
* 空输入 / 请求失败 / code != 0 / 无 data 都静默返回 `undefined`，不抛异常。

```text
search:export async function loadCategoryCode
search:} catch {
```

### TemplateEditorPage/index.tsx
`handleSave`

* edit 为 Patch：`templateMd` 仅 dirty 时带，`expectedVersion` 有值才带。
* success: 调 `onSaved`，但不主动 `onClose`；成功收尾归宿主。
* failure: 调 `resolveTemplateVersionConflictError`。

这与项目保存的「成功后必须 close」语义相反。

```text
search:resolveTemplateVersionConflictError(error)
search:onSaved?.()
```

### TemplateManageModal/service.ts
`resolveTemplateVersionConflictError`

* IDL 没有专用 version-conflict 错误码。
* 当前通过「版本冲突 / 已被更新 / version + conflict」关键词宽松匹配。

`updateTemplate`

* `expectedVersion` → `expected_version`
* 未传时整个协议字段省略。

```text
search:if (text.includes('版本冲突') || text.includes('已被更新'))
search:expected_version
```

## 2. 为什么这些事实值得缓存
|缓存|原因|
|---|---|
|create/edit `template_ids` 差异|跨分支协议差异；`[]` 与省略语义完全不同|
|项目必须 close / 模板不主动 close|两个业务成功收尾语义相反，局部阅读容易误判|
|分类文案 → 编码且失败静默|函数名无法暴露失败语义，错误使用会直接产生协议问题|
|version conflict 关键词匹配|反默认假设，不是错误码|
|reqId 竞态守卫|需要理解异步时序，不是单点结构事实|

默认不缓存：

* `submitting/loading` 等局部过程 state
* 普通 JSX 层级 / `contains`
* callers 列表
* 一次 grep 即得的叶子 API
* scope 外能力

判断标准就是 intelligence-contract.md「增」里的那一问：下个新窗口恢复它要多少源码阅读和业务推理。成本低就保持 cache miss。

## 3. owner 怎么定
owner 精确到 **symbol**，不是到文件：

|事实|owner|
|---|---|
|create/edit `template_ids`|`ProjectCreateEditPage/index.tsx` → `saveProject`|
|成功后必须 `onClose`|`ProjectCreateEditPage/index.tsx` → `handleSubmit`|
|分类文案 → 编码、静默失败|`useTemplateManageDialogs.ts` → `loadCategoryCode`|
|模板保存成功不 close|`TemplateEditorPage/index.tsx` → `handleSave`|
|version conflict 匹配方式|`TemplateManageModal/service.ts` → `resolveTemplateVersionConflictError`|

同一文件里 `saveProject` 与 `handleSubmit` 是两个 owner；`search:` 在文件里命中，不代表它能证明当前 section。

跨文件只引用，不复制。例如 `handleSave` 可以记录：

```text
- calls → TemplateManageModal/service.ts#resolveTemplateVersionConflictError
```

但不能把「关键词怎么匹配」复制进 `handleSave` 节；否则 service 改了而页面没改，副本会静默陈旧。

## 4. 最终 intelligence 应长什么样
只保留高价值语义，不复述源码：

```markdown
## src/pages/projectTeam/components/ProjectCreateEditPage/index.tsx
### handleSubmit
- calls → saveProject search:const saved = await saveProject()
success:
- create → onCreated；edit → onSaved；随后必须 onClose，否则与宿主预览面板叠层
  search:onCreated?.(savedProjectIdRef.current)

### saveProject
create:
- template_ids 非空才携带
  search:...(templateIds.length ? { template_ids: templateIds } : {})
edit:
- template_ids 始终携带；[] = 清空，省略 = 不生效
  search:template_ids: templateIds,

## src/pages/projectTeam/components/TemplateEditorPage/index.tsx
### handleSave
edit:
- templateMd 仅 dirty 时带；expectedVersion 有值才带
success:
- onSaved 后不主动 onClose；收尾归宿主
failure:
- calls → TemplateManageModal/service.ts#resolveTemplateVersionConflictError
  search:resolveTemplateVersionConflictError(error)

## src/pages/projectTeam/components/TemplateManageModal/service.ts
### resolveTemplateVersionConflictError
契约: version conflict 依赖关键词宽松匹配，不依赖专用错误码
search:if (text.includes('版本冲突') || text.includes('已被更新'))
```

## 5. 新窗口怎么查
问题：

> `edit template_ids` 传 `[]` 是什么意思？

```text
查 intelligence
→ 命中 saveProject/edit：「[] = 清空，省略 = 不生效」
→ 只核 search:template_ids: templateIds,
→ 证据仍成立，回答
```

不要重读上传、分类、failure，也不要重验整份文档。intelligence 没写就是 `unknown from intelligence` → 回源码，不能推出「不存在」。

### 回答形态
同一份 intelligence，换个问题就是另一种答案。`entry / target / expect` 只是回答记法，不是格式协议；Automation 要的是业务语义，不是 DOM selector——选择器由自动化 Agent 对着活 DOM 决定。

Business（改提交逻辑要动哪里）：

```text
项目编辑页「保存」 [ProjectCreateEditPage/index.tsx]
→ handleSubmit — success: onSaved 后必须 onClose，否则与宿主预览面板叠层
  → saveProject — edit: template_ids 始终携带；[] = 清空，省略 = 不生效  search:template_ids: templateIds,
```

Automation（自动化验证编辑关联模板）：

```text
entry   模板卡 ⋯ → 编辑               search:onClick: () => handleEditMountedTemplate(templateCard)
target  TemplateEditorPage「保存」        search:onClick={handleSave}
expect  POST /api/v1/me/templates/update search:'/api/v1/me/templates/update'
success toast「模板已保存」；关闭由宿主 onSaved 接管，编辑页不自行 close
failure version conflict → toast「内容已被更新，请刷新后重试」
```

## 6. 本例只校准三件事
1. **缓存什么**：只缓存高推理成本、易误解、会复用的业务实现语义。
2. **放在哪里**：证据在哪个 owner 的哪个 symbol，事实就归哪里；跨文件只引用。
3. **怎么消费**：先用 intelligence 缩小范围，再核 decision-critical source。

正常任务不需要读取本文件；只有抽取质量漂移、owner 归属混乱或不知道某类事实值不值得缓存时才加载。
