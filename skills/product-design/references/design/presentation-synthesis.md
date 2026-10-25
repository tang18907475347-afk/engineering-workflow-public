# Presentation Synthesis（开放式设计的构图参考）
> **这是提问工具，不是必答清单。** 当你需要重新想这块界面该是什么形态时来查；
> 不需要产出全部小节，也不要求按顺序走完。跳过某问而结论更好，是合法结果。
> 唯一值得保留的纪律：结构决策要能从任务拓扑解释，而不是从「现有 JSX 已经是 Table/Grid」倒推。

本文件帮助判断**这个模块的界面适合长成什么样**。结构本身不适合任务时，仅修缺陷可能保留错误形态；局部修复、审计或忠实实现则不因此承担重新设计结构的义务。

## 结构判断的参考关系
```text
User Goal → Task Priority → Information Priority → Interaction / Data Topology
→ Presentation Archetype → Component Morphology → Spatial Composition
→ Visual Hierarchy → Styling
```

这些维度可以互相启发或反复修订，不是单向流程。需要警惕的失败模式：从「现有 JSX 里已经有 Table / Card / 两栏 Grid」倒推「所以本轮优化 Table 的 spacing」——那是 implementation default，不是 design decision。

开放式重构中，结构问题可能比 styling 更值得处理；局部修饰或参考忠实实现任务则按用户目标工作，不要求先重做结构设计。

## 可选结构提问
需要判断当前模块形态时，可从这些问题中取用：

|#|问题|判据来自|
|---|---|---|
|A|**What is the visual center?** 用户第一眼最该看到什么|主任务 + 关键状态|
|B|**What is the primary action?** 这个页面主要让人完成什么|User Job / Handoff Target Outcome|
|C|**What information deserves hierarchy?** 逐项归入 `Primary / Supporting / Metadata / Exceptional`|真实字段与状态|
|D|**What interaction / data topology exists?** 例：sequence、comparison、hierarchy、creation、editing、monitoring、diagnosis、browsing、selection|数据形状 + 用户动作序列|
|E|**What presentation model best expresses D?** 结合任务、参考与现有约束选择，不仅凭当前组件类型决定|模型自己判断|

真实推导示例（无 reference 参与，只依据 Job + 现有代码/截图）：

```text
D: 配置任务有强制先后顺序（选候选 → 加外部 → 选测试集 → 定标准 → 发起），
   且完成度决定主按钮是否可用
E: 顺序配置流（带完成状态的节），不是对称两栏 Grid
   —— 两栏把「有先后的五件事」呈现成「同时存在的两摊信息」，
      于是左栏下方 60% 空白、主动作被埋在右栏中段
```

## Page Archetype
页面工作模型不清楚时，可以用一句自然语言概括以帮助选择组件，不要求每次产出 thesis。例：

```text
"This is a focused diagnostic workspace, not a record-management screen."
"This is a sequential configuration flow that ends in one irreversible launch,
 not a two-column settings form."
"This is a quality-gated inventory meant to be scanned and compared,
 not a discovery gallery."
```

**不建 archetype taxonomy、不建 enum、不建 registry。** 自然语言表达即可；目的是让页面有一个统一主张，使后续每个组件与间距决策可被同一句话裁决。

## Component Morphology 从任务语义推导
需要选择形态时考虑「**为什么这里适合这种组件形态**」（table / card / list / tree / split pane / composer / form / wizard / timeline / canvas / drawer / inline expansion / …）。

```text
数据/任务拓扑 → component morphology
```

不是：

```text
现有代码里已经是 Table → 优化 Table
```

判据举例：需要跨条目比较属性 → 对齐的列比卡片更有用；条目内部结构差异大且动作在条目内 → card / inline expansion 比 table 更合适；内容是顺序产出且用户读它 → 受约束的阅读栏宽度 + 专用滚动容器，而不是把消息裸挂进文档流；任务有强制先后 → 分步/带完成度的流，而不是并列 Grid。

**现有形态不适合任务时，允许直接替换或重组**，并在 Change 里写清「替换形态」的理由与被替换结构为什么是根因。

## Composition / Rhythm / Density
空间关系必须表达信息关系，而不是「把所有元素摆进容器」：

```text
section rhythm · vertical cadence · container widths · alignment lines
negative space · density · repetition · group boundaries
```

最低要求：

- 同一组内部距离 **<** 不同组之间距离；
- primary region 占据的视觉重量 **>** secondary region；
- metadata 比核心内容更安静；
- 主动作的 perceptual weight 明显强于次动作；
- 页面左右/上下视觉重量平衡，没有「无目的区域」（大片空白要么承载任务，要么收掉）。

**Density 是主动决策，不是默认值。** 禁止「更多留白 = 更高级」，也禁止「信息多就全塞满」。按任务判：工作台 / 诊断 / 开发工具通常允许高密度；新手引导与单任务创建需要聚焦；浏览/发现需要扫描效率与重复节奏。同一页面内保持一种密度口径。

**Consistency ≠ everything looks the same。** 真正的一致性来自 spacing rhythm、typographic hierarchy、control language、surface treatment、interaction conventions、color semantics；**组件形态仍应随任务变化**。禁止为了视觉统一把所有模块压成同一种 CRUD 模板，也禁止因为「别的页面是卡片」就在这里用卡片。

## Whole-page Visual Critique（实现后，先整体后局部）
评估实现时，可通过真实 Render / 截图看整体关系，按需参考：

```text
1. 第一眼看哪里？2. 为什么？3. 是否与任务优先级一致？
4. 是否有明确主区域？5. 组件形态是否服务任务？
6. 有没有不平衡或无目的区域？7. 信息是否正确分组？
8. 密度与节奏是否一致？9. 有没有「组件堆出来」的感觉？
10. 拿掉颜色、只看灰度与布局，hierarchy 是否仍成立？
```

这是 gestalt critique，不是 lint。发现的问题按可解释关系命名：

```text
weak hierarchy · unbalanced composition · wrong component morphology
fragmented grouping · inconsistent density · weak primary action
```

**禁止 beauty score**（`视觉质量 82/100` 之类没有可靠标尺），也禁止「看起来更高级 / 更现代 / 更漂亮」这种不可验证描述。Critique 发现的问题按本次授权处理：审计任务报告结论，实施任务修复范围内问题，并如实说明仍未解决的影响。

## 与 Reference Fidelity 的关系
体验是否适合任务，与实现是否忠实参考，是两个不同判断。参考、现有设计系统和用户明确约束可以从一开始参与设计，不必先独立合成再叠加。

用户要求忠实实现时，参考决定对应范围的形态；可以指出体验问题，但不擅自重设计。用户要求开放式改善时，参考是证据与灵感，可结合任务需要调整。无参考时仍可评估体验质量；高 fidelity 本身不证明体验合理。
