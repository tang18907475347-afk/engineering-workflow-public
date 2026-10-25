# Design Framework（工具箱，按需查阅，不是必做清单）
> 本文件是**知识**，不是流程。不需要逐项走完；哪一项真的有用再来查。跳过某项而结论更好，是合法结果。

## 可查的观察 / 诊断维度
从你怀疑最可能出错的地方开始，不必按顺序、不必全覆盖：

|维度|值得问的问题|
|---|---|
|Task & Flow|这些步骤 / 决策 / 输入里，哪些其实不该由用户做？|
|Journey & State Continuity|是否存在无价值步骤、重复输入、等待、回跳、context switch；跨步骤 / 跨模块是否保留对象、选择、进度、错误与上下文|
|IA / Navigation|用户能否预测去哪里完成任务；结构按用户心智模型还是历史实现组织|
|Information & Hierarchy|最重要的信息是否最先被理解；扫描路径是否成立|
|Interaction & Feedback|affordance 是否明显；成功、失败、异步、撤销、恢复是否形成闭环|
|Presentation & Composition|layout 是否表达信息结构；morphology 是否来自任务拓扑；视觉中心、分组、节奏、密度|
|Accessibility|keyboard / focus / labels / contrast / target size / reading order / status communication|
|States & Responsive|loading / empty / error / success / disabled 与不同 viewport 是否仍可用|
|实现资产|是否复用现有 tokens / components / conventions（复用资产 ≠ 继承构图）|

## Root cause 的 ownership 与 reach
满足任一项通常说明 root cause 的 ownership 在系统级：

- 完成一个 User Job 必须跨多个 surface 反复切换且状态 / 上下文不能自然延续；
- 解决需要改变任务顺序、导航 / IA、模块边界或核心 interaction model；
- 多个局部 surface 出现同一摩擦，根因来自共享对象模型、状态语义或全局信息结构；
- 当前界面按内部技术实体组织，而用户目标跨越这些实体。

判定纪律：

- `SHARED_SURFACE` 要求 root-cause ownership 位于多个 surface 共同消费的 shared 资产（component / token / shell）——一次根因修复同时修好多个 surface。
- **repeated causal pattern ≠ shared ownership**：同一 pattern 在多个 surface 各自独立实现，只说明同类清理有价值，仍各自记 local；不得因重复出现就升格成系统级根因。「多个页面都有 A11y 问题」不是共同根因，Finding 数量多也不推导「IA 必须重构」。
- 只有存在独立证据（同一实现机制、同一 shared 资产、同一状态链路）时才把多个 finding 提升为共同根因；证据不足时保留多个独立 findings 并写明还需什么证据。到此为止，不再往上抽象。
- **视觉与 presentation 的 ownership**：单个 surface 的构图 / morphology / 密度归该 surface；只有真正 shared 的层（global shell、全局导航层级、shared workspace architecture、design language、shared 视觉层级约定、shared 组件系统）才是系统级 reach。多个页面各自难看且成因独立 → 各自处理，不合并成「系统级视觉根因」。
- root cause 在更大 reach 不改变本轮实施义务：诊断与设计可以完整，是否一起改看任务 scope 与真实约束。

## Root-cause 闭合与 Change 类型
- `ROOT FIX`：改变已确认的机制，且验证同时确认机制与症状消除。
- `MITIGATION`：降低症状影响，未消除共同机制。
- `LOCAL IMPROVEMENT`：局部改善，与根因无关。

`Root Cause` 不是必填产物。`Diagnosis supported · Root cause unresolved · Next evidence: …` 本身就是合法终点；只有机制已确认时才要求同层级闭合——ROOT FIX，或明确 `ROOT FIX: BLOCKED BY PHASE CONSTRAINT / 当前动作是 MITIGATION`。结构性方案被阶段挡住时：指出真正根因 + 给出当前最小 intervention，说清两者不是同一件事。普通 polish 直接做完即可，不必为框架完整构造深层 root cause。

## 约束处理
|约束类型|对设计的作用|出现位置|
|---|---|---|
|`HARD`|参与设计推导：Target 必须满足，逐条写依据（法规 / 合规 / 外部协议 / compatibility / business invariant / security-safety / 用户明确长期要求）|设计依据|
|`PHASE`|**不否决诊断与结构设计**：只影响从现状到目标的路径与节奏（写解除条件与重评估触发）|交付路径|
|任务范围 / Out of scope|不是约束|Scope|

- **`Current Behavior ≠ Hard Constraint`**：Baseline 的 Behavior Contract 只说明「当前系统实际怎么工作」，不自动成为必须保持；改变重要 Current Behavior 时记录 `Current Behavior / Future Behavior / Reason / Impact`。
- 典型错误：用「当前阶段必须保持复刻保真」否决理想结构——那是把 PHASE 当 HARD；正确做法是设计照推导，把保真要求写进交付路径。
- 范围若只是任务范围就留在 Scope；只有真的阻止或限制了某个重要设计决定才登记为约束。

## Current / Target 与 Alternatives
- **materially different 判定**：只有在外貌维度（导航位置、页面名称、selector / 卡片样式、配色、文案）上不同 = 不算发散。至少在一条上不同才算：Core Entity 组织 / Entity Lifecycle / Journey 结构 / Capability grouping / Module boundaries / Persistent Context / Interaction model。
- 只有 evidence 真的留下**有意义的替代组织方式**时才探索多个方向；一个方向明显占优时直接收敛并写明其他方式为何被 evidence 排除。**禁止为凑数硬造第二方向**——凑数出来的「备选」会污染判断，也让 Alternatives 失去可信度。
- 反模式：换皮发散（结构相同只有导航不同）/ 机械反现状（仅因「现在是 5 个模块」就推导「应该合成 1 个」）/ 无依据最佳实践（行业惯例、竞品形态、「AI 产品都应该」）/ 大胆即失真（假设写成事实）/ ambition 伪装成计划（Target 直接写成一次性重写）。
- 「如果今天从零设计，还会保留这些模块边界吗？」是**触发提问**，不是结论模板：答案必须由 Job / Entity / Lifecycle / Capabilities / Context continuity / Decision points 推导——既不为显得大胆而机械废弃，也不以「现状能用」拒绝重新推导。

**Target 态探测问题（按需取用，不是必答清单）**——这些问题不回答，结构往往就没被真正重新推导：

1. 用户真正要完成的核心 Job 是什么？价值闭环在哪一步闭合？
2. 支撑这个 Job 的 Core Entity 是什么？它现在被拆散在哪些地方？
3. 该 Entity 的 lifecycle 应该由一个连续体验承载，还是现状的分段就是合理的？
4. 当前 module boundaries 是按理想产品组织出来的，还是历史实现 / 路由的产物？
5. 哪些「页面」其实只是同一个能力在不同上下文的出现形式？
6. 用户为什么需要在多个页面重复定位同一个对象？这个成本是结构必然还是可以避免？
7. Target IA 应该围绕任务、围绕实体，还是围绕角色 / 阶段？依据是什么？
8. Persistent Context 应该是显式的工作区对象、隐式的当前焦点，还是不存在？

## 同类问题扫描（可选，成本不低时使用）
只有当根因能明确映射成具体实现 pattern（如「固定宽度 master-detail 无响应式过渡」「有 pointer handler 但无 keyboard contract」「语义控件被换成 generic div」）时，才做一次 bounded same-pattern search。**命中只是候选**：相同代码形态不证明相同行为（`.catch(() => [])` 在一处吞了错误，另一处可能是合法的 optional fallback）；逐个确认后才写进结论，未确认的丢弃。

## Verification 层级定义
|层级|只证明这件事|常见误用|
|---|---|---|
|`PASS — CODE`|代码层成立（编译 / 类型 / 逻辑存在）|当成行为已验证|
|`PASS — DOM`|结构属性存在|当成 keyboard 已验证|
|`PASS — INTERACTION`|**指定的 interaction contract** 成立（真实操作路径走完）|点过一次按钮就算过|
|`PASS — VISUAL`|**指定的 presentation / visual claim** 成立（整页构图结论成立）|截图看起来没崩就算过|
|`NOT VERIFIED`|没做到的部分|省略不提|

这些 PASS 层级是**证据描述**，不是验收要求，也不映射为 TRR 状态；它们只说明本次实际验证到了哪一层。

```text
tsc PASS           ≠ behavior verified
DOM attribute 存在  ≠ keyboard interaction verified
screenshot PASS    ≠ interaction verified
code path 存在      ≠ runtime behavior verified
```

根因属于 interaction mechanism 时，只有 interaction-level 证据能宣称该问题已验证。支撑结论的证据落 `modules/<id>/verification/`（不落 `.engineering/work/` / `/tmp`）。

## Semantic Fidelity 检查（仅当任务有明确 replication / fidelity 约束）
比较 reference 与实现的**行为语义**，不做逐像素复制：interactive element semantics / focus / selection / keyboard behavior / open-close lifecycle / 默认展开折叠态 / loading-empty-error 语义 / interaction primitive。

真实失败样本：reference 的 `<button>` 被实现成 `<div onClick>`，selection anchor 被抢走导致插入内容污染用户消息；`<select>` 换成 Radio 组导致固定宽度容器挤压换行。

**差异本身不是缺陷**：只有当差异影响行为语义、明确 fidelity requirement、主任务完成或 accessibility 时才进入结论。UX 质量与 Reference 相似度是两条独立判定（见 skill-local `references/evidence-and-correction.md`）。
