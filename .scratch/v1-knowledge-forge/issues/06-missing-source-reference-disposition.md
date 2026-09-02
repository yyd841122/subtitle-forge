# 06 — 无 Source Reference 单元的下落

**What to build（单一产品增量）:** 无有效 Source Reference 的知识单元不进可信发布集，且在运行摘要/缺口报告有显性下落（状态取值与 Gap Category 归属由票内裁定——R2.4 明示属实现决策）。

**Spec anchors:** R2.4、A17。

**Blocked by（硬依赖）:** 03。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 06（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 替身产出无引用单元（其余正常）→ 该单元不在发布集
- [ ] run-summary 有其记录（状态可辨、reason 提「无来源引用」）
- [ ] gap-report 有指向它的条目；Source 的最终状态与 A4 语义一致（单元有下落即不妨碍 success——若票内裁定不同须记录理由）

**Implementation / code anchors:** `pipeline.py`（Ticket 01 基线 98–101 行，`source_reference is None` 的挡板）；`model.KnowledgeUnit.source_reference` 本就可为 `None`。

**明确不含（触界行为）:** 引用有效性分级体系（如 segment_id 不存在等细分场景，票内可顺手覆盖 locator 校验但须记录，不展开体系）。

**票内裁定:** **开工即先落**无引用单元的实体状态取值（rejected/failed 之一）与 Gap Category 归属，并记入票面（验收断言按裁定后的取值表达）。

**Spec 覆盖责任:** A17；R2.4。
