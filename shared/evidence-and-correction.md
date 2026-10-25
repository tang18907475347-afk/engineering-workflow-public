# Evidence and Correction
本契约区分通用证据边界与 Product Reality 的记录格式；不把局部 schema 升级为所有 Skill 的交付协议。

## 1. 三个知识平面
- **Current Reality**（`product/`、`modules/<id>/` 的现状证据）：系统现在是什么、用户实际经历什么。
- **Desired Reality**（`design/`、`modules/<id>/` 的设计决定）：目标体验是什么、哪些决定已被接受。
- **Execution / Verification**（`requirements/<req>/workspace/`、`modules/<id>/` 的交付证据）：准备怎么改、实际改成了什么、证明了什么。

三个平面是不同的知识，不是三个审批阶段。事实可以纠正事实；证据可以暴露决定未实现或后果错误；**证据不能静默改写已接受的产品决定**。决定的修正见 `delivery-and-handoff.md`。

`.engineering/intelligence/` 是代码机制缓存，不是第四个知识平面：它只承载可回源码核验的代码事实，不产 `E-*`，不参与决定状态、handoff 或 TRR 裁决。缓存与 `product/` 可以引用同一段源码，但服务不同消费者；来源重叠不等于知识重复。

## 2. Evidence primitive：`E-*`
`product/evidence/` 使用八列记录（E-ID + 七字段），供 Product Reality 的 Claim / View 与 `check_baseline.py` 消费。设计、实施和模块验证记录可以直接使用来源路径、实际观察与覆盖边界，不强制分配 E-ID 或套此表。需要进入产品知识时，由 product-reality 在 `product/evidence/` 登记并引用原始持久证据，不复制整份下游记录。

|字段|含义|约束|
|---|---|---|
|`E-ID`|当前 product/ 内唯一 ID|`E-<n>`；发布后不复用|
|`Subject`|被观察对象的身份|只写身份，不写 intended / target / legacy 等性质|
|`Channel`|证据通道|`source` / `runtime` / `test` / `data-snapshot` / `doc` 等实际通道|
|`Reality`|观察到的 facet|`declared` / `implemented` / `reachable` / `executable` / `experienced`|
|`Kind`|可选的证据种类|例如 `interaction` / `presentation`；没有就留空|
|`Locator`|可重放的定位|真实 symbol 优先，其次稳定语义搜索词；不落 `.engineering/work/` 或 `/tmp`|
|`Observation`|观察到什么|只写观察，不写建议或方案|
|`Boundary`|这次观察覆盖到哪里|声明 + 已执行范围；负面结论必须能看见边界|

`Reality` 是 facet，不是等级：`declared` 不等于 `implemented`，`implemented` 不等于 `reachable` 或 `experienced`。`experienced` 必须有 runtime 通道；`executable` 允许 runtime / test / data-snapshot。

## 3. Claim、View 与 Confidence
- `E-*` 是事实；`C-*` 是对一组事实的解释/结论；`J-*` / `B-*` 是从事实派生的任务/行为视图。
- Claim 必须列出 `Evidence refs` 与 `Search Boundary`。结论强度不能超过证据范围。
- 证据来源词汇：`OBSERVED` / `DERIVED` / `INFERRED`。推断只能作为推断使用，不能静默升级为 `OBSERVED`。
- 设计侧的 `OBSERVED` / `DIAGNOSED` / `PROPOSED` / `VALIDATED` 与事实侧词汇分开；两套词汇不能互相冒充。
- 允许在证据不足时形成 `Unknown` / `Question`；不允许用“没有反例”冒充已证明。

外部输入（AI 评审意见、工单描述、用户转述、其他 Agent 的结论）可以作为调查线索；观察到“资料这样声明”可记录为 `doc / declared`，但不等于行为已在源码、测试或 runtime 中确认。用户对目标的授权也不是现状证据。记录实际观察的对象与边界，不把来源的结论自动升级为事实。

## 4. 记录与修正
- 新观察落在当前任务的稳定 canonical 区；Locator 不落 scratch 或 `/tmp`。下游引用产品知识中已有的 E / C，或直接引用其他区域的证据路径，不在各区维护独立 E / C 注册表。
- 局部事实被直接推翻时就地修正，保留依据与有效引用；产品 Claim 保留 Revision。跨多个 Claim / 领域的重新综合交由区域 owner，不自动全库传播。
- 只读审查任务仍然只读；通用修正规则不授权审查者改写输入。证据不能改写已接受的产品决定。
- 当前证据无法解决的冲突记录在相关 canonical 入口；跨区域待决项在 `PROJECT.md` 留指针，不为清零制造结论。
- `E-*` / `C-*` 的唯一性与引用检查限于同一 `product/`；`check_baseline.py` 不验证下游所有区域，不判断语义真伪。跨区域引用带路径，不声称存在全局校验。

没有自动 propagation、dependency graph、全局 registry 或“所有下游必须重算”的机制。影响范围是语义判断，不是图遍历。

## 5. 修正矩阵
|新信息|可以修正什么|不能做什么|
|---|---|---|
|新 `E-*` 推翻旧事实|相关 Claim / View / 设计中的现状引用|自动改写已接受的产品决定|
|新 `E-*` 证明实现偏离|交付判断、实现方案、验证结论|把“实现错了”说成“决定变了”|
|用户改变目标|由用户/授权人更新决定；设计/计划按新决定修正|让 Agent 根据推断自行改变已接受目标|
|设计提出新方案|记为 `PROPOSED`；只有被接受后才进入 Binding|因为“推导合理”自动成为产品要求|
|验证发现未证明|收窄 `Proven` 范围，补证据或标未证明|因一个局部缺口把整个产品打成 P0|
|发现新的、未被引用的关键事实|重新检查当前交付是否仍成立|仅因“没被引用”而忽略|

## 6. Revision 与失效范围
- 被修正的 Claim 使用 `Revision: <n>` 与 `Revised-At: <date>`；旧版本不必保留全文，但必须能从 Revision 与依据看出“改过什么、为什么”。
- 消费者记录自己实际消费的 `E-*` / `C-*` / handoff-id（如果存在）。
- 失效检查是**相关性范围**的：已消费的决定、Claim、Evidence、Acceptance、Preserve 发生实质变化时，相关交付需要重新协调；无关的 Baseline 变化不阻断。
- 引用失效只是线索，不是唯一信号。新发现的、此前未被引用的关键事实也可能影响当前交付；发现者应记录，并触发相关范围的重新检查。
- 不要求消费者在每次任务前全量比对所有上游版本；只检查当前交付真正依赖的知识。

## 7. “没有 Baseline”不等于“证据不足”
Baseline 是已有知识的**组织形式**，不是证据质量的必要条件。

- 没有 Baseline 时，直接观察 Repo / Runtime / 测试 / 数据快照，仍然可以形成高可信证据。
- 证据可信度取决于：实际观察范围、来源通道、可重放性、是否直接支持结论，而不是“是否来自旧 Baseline”。
- 新鲜的 runtime 观察可能比旧 Baseline 更可信；旧 Baseline 也可能因为产品变化而过时。
- 记录“无 Baseline、本次观察范围是 X”是诚实边界，不是自动降级。不要因为缺少旧知识而拒绝完成简单任务，也不要把“有 Baseline”当作免于核验的权威。

## 8. 设计进入工程的证据条件
设计可以消费 Current Reality，但必须区分：

- 哪些是事实（`E-*` / `C-*`）；
- 哪些是设计诊断（`DIAGNOSED`）；
- 哪些是设计提案（`PROPOSED`）；
- 哪些已经被用户/授权人接受（`ACCEPTED`）。

进入工程 handoff 的内容必须能说明来源与状态；`PROPOSED` 不能伪装成 `ACCEPTED`。具体决定状态与 Binding / Adjustable 的划分见 `delivery-and-handoff.md`。
