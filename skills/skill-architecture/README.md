# skill-architecture
判断已有 Skill / Plugin 的架构。重建真正塑造模型行为的系统，判断知识、工具、状态、权限、流程与模型判断之间的责任分配，依据真实根因与证据决定保持、局部修正还是结构性重构。

它不提供统一最佳实践，不默认追求更少 Skill、更少文件或更少机制，也不默认重构优于保持。

## 文件
- [SKILL.md](SKILL.md)：运行时契约、立场与结果要求。
- [references/behavior-surface.md](references/behavior-surface.md)：行为面清册与重建方式。
- [references/allocation.md](references/allocation.md)：按机制类型的责任分配判断。
- [references/observed-failures.md](references/observed-failures.md)：真实发生过的失败，按机制命名，可从症状进入。
- [references/evidence-and-scale.md](references/evidence-and-scale.md)：证据分级、变更尺度、张力裁决。
- [references/format-compression.md](references/format-compression.md)：审计结论为仅压缩表达时的流程、可压 / 不可压边界与验证证据。

## 边界
- 不是 Skill 创建器；不做格式、规范符合性或最佳实践评分。
- 静态材料无法证明的行为问题停在「需要行为验证」，不向上补全成结论。
- 用户个人偏好可以影响具体项目的裁决，但不进入通用知识层，也不写成设计原则。
- 不保留历史兼容：改名、边界或结构判断要求切换时就彻底切换。

## 维护
- 明确请求经验整合时，以新证据修正、替换甚至推翻已有认识；过时、重复或不再改变判断的知识删除，不要求新旧原则并存。新失败先并入 [observed-failures.md](references/observed-failures.md) 已有机制，仅无法归入且会改变判断时才新增。
- 失败记录只保留真实形态、代价与适用边界，不复述原则或复制审计报告。已确认的契约 / 实现缺陷与尚未验证的行为收益分别表述，不以改动完成证明能力改善。
- 新增 reference 需要独立的问题域。同一主张不要在两处独立定义：若两处会在同一次运行中同时加载、且都能各自改写语义，就必须指定一处为权威。索引与正文、摘要与展开、原则与实例不算重复，它们职责不同。
- 运行时判断需要的知识进入 references/SKILL.md；维护政策只留 README。经验整合不是每次任务后的自我审计，不新增自动吸收、定期评测、优化循环或经验登记系统。
