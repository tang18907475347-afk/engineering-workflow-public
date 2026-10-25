# Module Handoff: <module-id> / <handoff-id>

<!-- canonical 路径：.engineering/design/module-handoffs/<module-id>/<handoff-id>.md
     生成前提：存在真实下游消费者，且需要知道“工程当时消费的是哪个设计版本”。
     同一上下文连续完成的设计+实现、简单 UI 修改不需要创建本快照。
     本文件是信息传递，不是审批单。发布后正文不可变；Status / Superseded-By 可更新。 -->

- Status: READY | BLOCKED | SUPERSEDED
- Superseded-By / Reason:（Status=SUPERSEDED 时填写）
- Consumer Record:（消费者填写：任务 / 日期 / 消费的 handoff-id）

## Problem / Intent

<!-- 这个 surface 要替用户解决什么，本轮为什么要动它 -->

## Binding

<!-- 只有已接受决定、其严格必要推导、由接受决定直接定义的 Preserve / Verification Obligation 可以进入这里 -->

### Accepted Decisions

<!-- D-* / Statement / Authority / Accepted-At / Scope -->

### Strict Derivations

<!-- D-* / Derived-From / 为什么没有它，被接受的约束无法成立 -->

### Preserve

<!-- 已接受决定中不能被破坏的行为、语义或约束 -->

### Verification Obligations

<!-- 必须证明什么；不规定具体测试实现 -->

## Adjustable

<!-- 设计提案、开放问题；不得伪装成 ACCEPTED 或 Binding -->

### Proposed Design Choices

<!-- D-* / Status: PROPOSED / Basis -->

### Open Questions / Dependencies

<!-- 仍允许工程层探索的问题；被 PHASE 挡住的结构问题（需要突破哪一层 + 当前最小动作） -->

## Relevant Evidence

<!-- E-* / C-* / B-* / 路径 + 小节；不重抄长证据 -->

## Hard Constraints

<!-- 真正不能被违反的条件，逐条写依据；普通任务范围留在 Problem/Intent 里说，不升级成约束 -->
