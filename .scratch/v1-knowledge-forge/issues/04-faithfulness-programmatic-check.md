# 04 — 忠实性审计的程序比对（假引用拦截）

**What to build（单一产品增量）:** 即使推理审计替身判「通过」，凡 `quoted_text` 无法在所指 Source 的原文中程序比对成立的单元，一律不进可信发布集，并以 `audit_rejection` 落缺口报告。审计门自此 = **程序比对 ∧ 推理审计** 双通过。

**Spec anchors:** R3.1、A1、Implementation Decisions 2/5（忠实性审计含纯程序比对部分，不经由生成同一内容的替身自评）。

**Blocked by（硬依赖）:** 03（复用拒绝下落机制）。

**Status:** done (2026-09-02, Codex 独立复审 READY / 0 blocking / 0 findings)

**Materialized from:** plan v2.2 票 04（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [x] 替身产出「引用文本不存在于原文」的单元 + 审查替身 `pass` → 该单元不在发布集
- [x] gap-report 的 `audit_rejection` 条目可辨原因来自忠实性比对
- [x] 同 run 中真引用单元照常通过（比对不误伤）

**Implementation / code anchors:** `pipeline.py` 单元准入段（`_trusted_entry` 之前）；`Segment.text` 为比对基准（`ass.py` 保留解析后原文形态）。

**明确不含（触界行为）:** 比对容差的真实数据调优（票内先裁初始算法即可）；推理审计角色本身的行为（03 票）。

**票内裁定:** Open Impl 10 初始算法（精确匹配或最小规范化后匹配）；该检查在管线中的位置（发布集准入前的程序门，不经任何认知角色）。

**Spec 覆盖责任:** A1；R3.1。

> 票内裁定落定记录（2026-09-02 done）：初始算法 = 最小规范化后匹配（空白连续段
> 含换行折叠为单个空格 + 去首尾，逐字子串、锚定所指 segment_id；空引用与悬空
> segment_id 均不成立）；程序门位于发布集准入前（pipeline.py，`_trusted_entry`
> 之前），不经任何认知角色；拒绝理由以「忠实性比对不成立」为稳定前缀（缺口条
> 目与运行摘要据此可辨来源）。悬空 segment_id 与 locator 一致性校验：前者随本票
> 落地为忠实性拒绝，locator 与所指片段的一致性校验不属本票（比对容差范畴，
> 未拆票前不做）——cc-suite audit 遗留观察，见
> `.cc-suite/audits/audit-20260902-184904-findings.md` #1。
