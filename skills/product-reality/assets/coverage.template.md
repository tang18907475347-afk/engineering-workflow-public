# Coverage — <Area>

## Inventory Coverage

<!-- 分母来自 reconnaissance Inventory（Surface / Route / API / Runtime Executor / Authoritative Docs / Persistence / Background Job / admin-config-legacy 等类型），
     **不由 Question Ledger 自己生成**——否则模型漏掉的对象永远不会出现在 Coverage 里。
     Baseline Relation 相对于 Baseline Scope；Spec Relation 相对于 Spec Target Scope（无 spec 时写 —）。
     Disposition（每个 scope 独立）：
       Baseline Disposition — 对 Baseline Relation 的 in-scope/dependency 项；COVERED/EXEMPT/OPEN。
       Spec Disposition     — 对 Spec Relation 的 in-scope/dependency 项；COVERED/EXEMPT/OPEN；无 spec 写 —。
       COVERED — 必须链接 ≥1 条 Q-/E- ref；有行为契约时必须列出相关 B-* 并确认每个 B-* 已处置；
                 Surface 类同时填 Classification。
       EXEMPT  — Reason 必须相对于当前 Target Scope，并有证据：完整 Baseline 用不变量 2 判断是否产品面；
                 Replica-Ready 用「不在 Spec Target Scope」或「依赖内部与目标行为无关」。
                 不得仅以「不是 User Job」「属内部实现」「非产品面」排除 Spec Target Scope 内的系统能力。
       OPEN    — 尚未处置；COMPLETE 前必须清零，或逐项转入 Unknown Registry 并标明是否 blocking。
     Inventory COVERED 不等于行为契约已恢复；一个 item 可以对应多个 B-*。
     某类型 0 项时，在下方 Type Completeness 写明是「确实不存在」还是「未找到 + 检索方式」。 -->

| Inventory Item | Type | Baseline Relation (in-scope/dependency/out-of-scope) | Baseline Disposition (COVERED/EXEMPT/OPEN) | Spec Relation (in-scope/dependency/out-of-scope/—) | Spec Disposition (COVERED/EXEMPT/OPEN/—) | Classification（Surface 类填） | Q-/E-/B- refs | Reason (EXEMPT/OPEN 必填) |
| -------------- | ---- | --------------------------------------------------- | ------------------------------------------ | -------------------------------------------------- | ---------------------------------------- | ------------------------------ | ------------- | ------------------------- |

## Type Completeness

<!-- 逐类型确认非空或说明缺失原因；运行期执行器与权威文档两类为空是高风险信号 -->

| Inventory Type | Item 数 | 若为 0：确实不存在 / 未找到（附实际检索方式） |
| -------------- | ------- | --------------------------------------------- |

## Objects

| Object | Lifecycle Stage | Related J-ID | Status | Search Boundary | Claim/Evidence refs |
| ------ | --------------- | ------------ | ------ | --------------- | ------------------- |

## Journeys（广度）

| J-ID | Continuity Dimension | Status | B-ID / Claim refs |
| ---- | -------------------- | ------ | ----------------- |

## Journey 深度轴

<!-- 只登记 `P0/P1 且 UI-bearing` 的 Journey；无 UI 的 P0/P1 Journey 不登记（它没有 interaction / presentation / experience 事实）。不要扩到全部对象/Surface（那是无差别 checklist 化）。
     取值：PRESENT | N/A(理由) | MISSING。
     PRESENT 的判据是存在对应 Kind 且 Reality 匹配的 E-*，不是「Journey 散文里提过」。
     任一 P0/P1 UI Journey 出现 MISSING → 不得 COMPLETE。规则唯一权威：`references/product/coverage-and-readiness.md` §3。 -->

| J-ID | interaction (`Kind: interaction`) | presentation (`Kind: presentation`) | experience observed (`Reality: experienced`) | Evidence refs |
| ---- | --------------------------------- | ----------------------------------- | -------------------------------------------- | ------------- |

## Cross-domain Handoffs

| Handoff | Status | Claim refs | Gap |
| ------- | ------ | ---------- | --- |

## Unresolved

| U-ID / Q-ID | Potential P0/P1 Impact | Status | Required Authority |
| ----------- | ---------------------- | ------ | ------------------ |
