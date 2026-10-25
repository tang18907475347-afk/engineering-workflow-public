# Surface Work — <module-id>

<!-- 骨架不是清单：只写你真的得出的东西。没有替代方案就不写「方案比较」，
     机制没确认就不写「root cause」，没验证就写 NOT VERIFIED，不要为填满模板造内容。 -->

- Status:
- User Outcome（这个 surface 替用户完成什么）:
- Evidence read（引用了哪些 `E-*` / `C-*` / `B-*`，哪些是本轮新观察）:
- Upstream / Handoff: # design/ 当前有效决定，或 design/module-handoffs/<module-id>/<handoff-id>.md 及其 Status（仅存在真实下游消费者时）

## Diagnosis

<!-- 你判断真正的问题是什么、机制是什么。可以包含超出本轮 implementation reach 的根因——
     讲清楚它为什么是根因，以及当前 scope 下最小的 intervention 是什么。 -->

| #   | Observed | Diagnosis | User Impact | 归属（本 surface / shared / 系统级） |
| --- | -------- | --------- | ----------- | ------------------------------------ |

## Design Decision

<!-- 决定把它改成什么形态，以及为什么这个形态更贴合任务拓扑（不是「因为参考这样」也不是「因为更现代」）。
     需要重新想结构时可借用 references/design/presentation-synthesis.md 的提问工具，不必逐条填。 -->

## Changes

| #   | 改动 | 影响面 | 是否本轮实施（受 scope 限制） |
| --- | ---- | ------ | ----------------------------- |

## Verification

<!-- Result 只写实际达到的层级，每层只证明自己那件事：
     PASS — CODE / DOM / INTERACTION（指定 interaction contract）/ VISUAL（指定 presentation claim）/ NOT VERIFIED。
     证据放 modules/<id>/verification/，不落 /tmp 或 .engineering/work（不可重放）。 -->

| 项目 | Result | 证据 |
| ---- | ------ | ---- |

## Unknowns / 未解决

<!-- 包括：判到系统层但本轮不改的根因（同 Skill 内后续处理）；无法验证的部分；需要突破的结构层级与触发条件。 -->
