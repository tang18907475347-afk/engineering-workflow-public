# 代码库与产品侦察协议
> 本协议用于建立完整 `product/` 现实或大型逆向。轻量代码问题不需要先做 Inventory；直接回答、当前问题闭合即停，零写入是合法结果。反过来，复刻、结构性重构或系统理解目标要求目标范围内的完整性时，不适用「最小调查」；Inventory 与 Trace 必须覆盖目标范围内的相关 Surface、运行期执行器、权威文档、异常/取消/重试/恢复路径与跨模块状态关系。

## 1. Inventory（导航起点）
先建立导航图，不急着形成 User Job：

- 应用/服务/包与主要入口；
- Routes / 页面 / 主 CTA / 命令或外部入口；
- API/Action/事件入口；
- Store/Schema/Model/Migration/Persistence adapter；
- 后台任务/队列/调度；
- tests/fixtures/examples；
- 明显的 admin/config/legacy 区域；
- **运行期执行器与产出机制**：executor / runner / tool 挂载点、素材与上下文装载、产出物形态与其门禁、失败与回退路径——要定位到本体，不能只记下名字；
- **权威文档目录**：repo 内说明文档 / 契约文档 / README / 设计说明（作为 source 之外的第二证据通道入口，见 §2）；
- **每个 Subject 的对应 Surface**：多 Subject 项目（replication / fidelity / 对照 / 迁移）里，`reference` 与 `implementation` 是**两个一等 Subject**，各自的 P0/P1 界面、route、nav 项、工作台形态都要进 Inventory 分母，并在 Evidence 上标各自的 `Subject`。**不是**「reference 场景的特殊附加项」，也**不是**把两边合并成一份 Surface Inventory——后者会让同名功能塌成一个 Subject。单 Subject 项目只有一个 `self`。否则 reference 体验根本不在 Coverage 里，永远不会被检出遗漏——这与「分母不能只由被测仓库自己生成」是同一个问题。

Inventory 只证明「存在与位置」，不证明「用户任务是什么」。写入 `product-model` 与 `coverage/surfaces.md`。

**Inventory 同时是 Coverage 的分母**：每个 Inventory item 后续都必须在 Inventory Coverage Ledger（`coverage/surfaces.md`）里拿到 disposition，所以采样时按类型清单逐类过一遍。某类型 0 项时必须写明是「本项目确实不存在」还是「没找到、检索方式是 …」——运行期执行器与权威文档两类为空是高风险信号。

其中三类是 `scripts/check_baseline.py` 的必需盘点类型：**Surface、Runtime Executor、Authoritative Docs**（缺行，或为 0 项而无 zero-result 说明 → ERROR）。修改本清单时同步脚本里的 `REQUIRED_INVENTORY_TYPES`。

Inventory 的目标范围由用户目的决定；复刻/重构时必须覆盖目标范围内的相关类型，不能用最小导航集合代替完整性。

Inventory 记录必须包含两个关系字段：`Baseline Relation: in-scope / dependency / out-of-scope`（相对于 `Baseline Scope`）与 `Spec Relation: in-scope / dependency / out-of-scope / —`（相对于 `Spec Target Scope`；无 spec 时写 `—`）。Baseline Coverage 的 disposition 对 Baseline Relation 的 `in-scope` / `dependency` 项要求；Replica-Ready 的 disposition 对 Spec Relation 的 `in-scope` / `dependency` 项要求；两边 `out-of-scope` 都只记录边界。**Inventory COVERED 不等于行为契约已恢复**；行为完整性由 `B-*` 表达，Inventory 只回答发现了哪些能力、入口、对象及依赖。跨边界调查允许，但发现项按两个 Relation 分类，不自动纳入复刻范围（见 `coverage-and-readiness.md` §8.1）。

## 2. 搜索优先级
默认顺序：

1. Symbol / definition / reference / call hierarchy；
2. 精确文本搜索：route/action/endpoint/object/state mutation；
3. 读取局部上下文；
4. 只有跨文件关系仍不清楚时才读整文件；
5. 只有当前 Question 需要时才做更广目录扫描。

禁止从头顺序阅读整个仓库作为默认策略。

## 3. Top-down Vertical Slice
从用户可达 Surface 追：
`Surface → User Action → Handler → State/Request → Domain Logic → Persistence/Background → Response/Event → Observable Result`

每段记录：位置/符号、输入输出、状态变化、是否用户可观察、Evidence ID。

Top-down 适合回答：真实 Journey、Action 语义、门禁、错误反馈、异步状态。

## 4. Bottom-up Object Lifecycle
对每个核心对象追：
`create/import → inspect/use → modify → validate/approve → publish/share/export → archive/delete → history/recover`

每阶段只能标：`SUPPORTED / UNSUPPORTED_WITHIN_BOUNDARY / UNRESOLVED`。记录 write/read sites、消费方、可观察效果与 Search Boundary。

Bottom-up 用于发现：隐藏 mutation、后台行为、跨页面共享状态、同一对象多入口、历史/恢复链路。

## 5. Reachability 检查
源码存在不等于当前产品可达。对重要能力区分：

- `REACHABLE`：有当前入口/调用链；
- `HIDDEN_REACHABLE`：无普通入口但存在有效可调用路径；
- `LEGACY`：历史链路仍存在但不属于当前主体验；
- `DEAD/UNUSED_WITHIN_BOUNDARY`：在声明范围内未发现消费者；
- `UNRESOLVED`：证据不足。

## 6. Behavioral Triangulation
高影响结论尽量交叉验证：

- runtime + source；
- source + test；
- source + authoritative docs；
- UI observable + state/persistence trace。

不要为了满足形式增加无价值证据；第二证据通道的目的只是挑战第一解释。

## 7. Negative Search
「不存在/唯一/全部」必须先定义边界，例如：
`frontend API client + route registry + domain service + related tests`

在边界内未发现可以写：`在该 Search Boundary 内未发现 X`。禁止直接写：`系统不存在 X`。

## 8. Contradiction Follow-up
发现冲突时先记录双方 Evidence，不自动选看起来更合理的一边。根据 Claim 类型决定需要什么额外 Authority；无法解决且影响 P0/P1 时保持 `PARTIAL`。

## 9. 产品考古与系统诊断的边界
**考古不新增独立维度**：历史阶段、遗留功能、旧设计意图、Demo 演化阶段，全部由 `Subject` + `Reality` + `Kind` + Evidence 上下文 + legacy 分类表达（例：某功能 `Reality: implemented` 且 Intent 来自 docs/stakeholder，而 experienced 缺失 → 说明是历史残留或半成品）。禁止新增 `history/` 产物族、archaeology registry 或 era model——真实案例证明无法表达时再考虑。

两者都**只服务 Product Reality**，不是工程健康检查。

**产品考古**回答「现在看到的系统为什么是这样、哪些东西来自不同历史阶段」。允许调查：git/history（若可用）、docs 版本、旧/新 UI、dead 但有意义的代码、route 演化、命名矛盾、feature flag、未完成的 integration、reference 与 current 差异、stakeholder 解释。**只有当它能解释 Product Intent / Journey / System Completeness / Contradiction 时才调查**；禁止为考古而考古，禁止全面 git history mining。

**系统诊断**检查范围限于：P0/P1 Journey 是否闭合、critical executors 是否接线、UI / Source / Runtime 是否一致、关键 output 是否真的产生、模块之间是否断链。**不扩展为 architecture / performance / security / code-quality / test-coverage audit**，除非它们直接阻塞某条产品 Journey。

**不打完成度分数**：「哪些链路成立、哪些不成立、为什么不知道」比 `63% 完成度` 这类合成评分更有价值，也更难被误用。
