# Design — <scope / name>

<!-- 骨架不是清单：只写你真的得出的东西。没有结构分叉就不写 Alternatives，
     没有受约束交付就不写 Delivery，假设未被验证就保持 PROPOSED，不要为填字段造内容。 -->

- Status:
- Scope / Intent / Outcome:
- Evidence read（引用了哪些 `E-*` / `C-*` / `B-*`，哪些是任务内新观察）:

## Upstream References

<!-- Provenance / navigation：路径 + 稳定 ID。不是依赖图，也不构成新鲜度证明。 -->

- product/…
- modules/<module-id>/…

## Evidence & Constraints

<!-- 只登记真正影响设计决定的事实与约束；HARD 逐条写依据，PHASE 写解除条件与重评估触发。
     普通任务范围留在 Scope / Out of scope，不升级成约束。 -->

## Current → Target

<!-- Journey 阶段与决策点（不是页面清单）与关键结构变化：Experience Architecture / IA / Workspace /
     Interaction / Presentation。改变重要 Current Behavior 时记录 Current / Future / Reason / Impact。
     Target Journey 是设计产物，不占用 Current Reality 的 J-* 身份、不回写 Current。 -->

| #   | Current | Target | Reason / Tradeoff |
| --- | ------- | ------ | ----------------- |
|     |         |        |                   |

## Design Decisions

<!-- 每条决定包含 Status（PROPOSED / ACCEPTED / SUPERSEDED）与 Basis（DECISION / EVIDENCE / DERIVATION / DESIGN_JUDGMENT）。
     只有 ACCEPTED 决定、其严格必要推导、由接受决定直接定义的 Preserve / Verification Obligation 可以进入工程 Binding。
     Decision / Basis / Authority / Tradeoff / 证伪方式。
     机制已确认的根因闭合写 ROOT FIX 或 `BLOCKED BY PHASE CONSTRAINT` + 当前 MITIGATION；
     未确认时写 `Diagnosis supported · Root cause unresolved · Next evidence: …` 是合法结果。 -->

| #   | Decision | Status | Basis | Authority | Tradeoff | 证伪 / Validation |
| --- | -------- | ------ | ----- | --------- | -------- | ----------------- |
|     |          |        |       |           |          |                   |

## Alternatives

<!-- 仅当存在结构上真正不同的方向时才写：在哪个结构维度不同 / 为什么未选。
     一个方向明显占优时，写一行说明为什么其他组织被 evidence 排除即可；禁止凑数。 -->

## Delivery Implications

<!-- 仅当任务包含受约束交付时：现状 → Target 的主要 gap、可渐进方式（共存 / 局部先行 / 双轨期）、
     Delivery Constraints（原 PHASE，含解除条件）、被 PHASE 挡住的结构缺口。
     不自动生成实施 roadmap，除非任务明确要求。 -->

## Open Questions / Unknowns

<!-- 高影响 Unknown、超出本轮 reach 的结构问题：需要突破哪一层 + 当前最小动作。 -->

## Module Handoffs

<!-- 只为有真实下游消费者、且需要版本追溯的 module 生成 canonical 文件
     （design/module-handoffs/<module-id>/<handoff-id>.md）。
     同一上下文连续完成的设计+实现、简单 UI 修改不需要 snapshot。
     本 phase 无 surface action 的设想留 Revisit Trigger，不生成空转 handoff。
     此处只列已生成 handoff 的索引。 -->

| module-id | handoff-id | Status | Handoff path |
| --------- | ---------- | ------ | ------------ |
|           |            |        |              |
