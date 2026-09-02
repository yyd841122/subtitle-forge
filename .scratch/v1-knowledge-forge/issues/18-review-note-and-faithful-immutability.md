# 18 — Review Note 产出与忠实层不可篡改

**What to build（单一产品增量）:** 审查环节确认并产出正式 Review Note（`review/` 层、标注系统判断），忠实层内容保持与原文一致不被修改；提炼阶段的疑点信号不直接落为正式注记。

**Spec anchors:** R2.5、R3.6、R3.7、A9。

**Blocked by（硬依赖）:** 03。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 15（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] **字节基线**：对同一提炼输出分别运行「审查确认」与「审查不确认」两次 → 两份忠实层资产**逐字节相同**，差异只出现在 review/ 层
- [ ] 提炼替身带 `extraction_doubts` 且审查确认 → review/ 出现正式注记（含 source_id、对象、内容、「系统判断」标注）
- [ ] 只给提炼疑点、审查不确认 → 无正式注记
- [ ] **R3.7 结构化落实**：Note 的 schema 只含观察/风险描述字段，**不提供权威更正（authoritative correction）字段**——以资产结构断言约束「只表达存疑，不裁决真伪」

**Implementation / code anchors:** `model.extraction_doubts`（信号已备）；`assets.py` review/ 占位目录；审查角色输出结构需扩展。

**明确不含（触界行为）:** 注记的管理/消费界面；忠实层「不可篡改」的密码学保证（产品语义 = 系统路径不写改，A9 场景断言）。

**票内裁定:** 产出注记的角色归属（扩展推理审计结论 or 独立注记职责——最小改动为准）；Note 文件的 schema 与位置（受上述 R3.7 约束）。

**Spec 覆盖责任:** A9；R2.5、R3.6、R3.7。
