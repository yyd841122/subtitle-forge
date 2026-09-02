# 04 — 忠实性审计的程序比对（假引用拦截）

**What to build（单一产品增量）:** 即使推理审计替身判「通过」，凡 `quoted_text` 无法在所指 Source 的原文中程序比对成立的单元，一律不进可信发布集，并以 `audit_rejection` 落缺口报告。审计门自此 = **程序比对 ∧ 推理审计** 双通过。

**Spec anchors:** R3.1、A1、Implementation Decisions 2/5（忠实性审计含纯程序比对部分，不经由生成同一内容的替身自评）。

**Blocked by（硬依赖）:** 03（复用拒绝下落机制）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 04（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 替身产出「引用文本不存在于原文」的单元 + 审查替身 `pass` → 该单元不在发布集
- [ ] gap-report 的 `audit_rejection` 条目可辨原因来自忠实性比对
- [ ] 同 run 中真引用单元照常通过（比对不误伤）

**Implementation / code anchors:** `pipeline.py` 单元准入段（`_trusted_entry` 之前）；`Segment.text` 为比对基准（`ass.py` 保留解析后原文形态）。

**明确不含（触界行为）:** 比对容差的真实数据调优（票内先裁初始算法即可）；推理审计角色本身的行为（03 票）。

**票内裁定:** Open Impl 10 初始算法（精确匹配或最小规范化后匹配）；该检查在管线中的位置（发布集准入前的程序门，不经任何认知角色）。

**Spec 覆盖责任:** A1；R3.1。
