# 19 — 聚合知识层（三层钉死）

**What to build（单一产品增量）:** 提炼产出聚合知识，**要点（key points）/ 主题（themes）/ 概要（overall summary）三层形态全部落地**（替身受控产出各层至少一条，不评内容质量）；资产同时含知识单元层与聚合层；聚合知识不携带单元级实体状态、不进单元级对账、不进单元级通过率分母。

**Spec anchors:** R2.1、R2.3、A18。

**Blocked by（硬依赖）:** None。注意：21 票硬依赖本票（指标排除断言以聚合存在为前提）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 16（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 正常运行后资产含单元层 + 三层聚合（人可读 + 机可解析）
- [ ] 聚合条目无单元级 status、不出现在运行摘要的单元对账中

**Implementation / code anchors:** `roles.ExtractionOutput`（扩展聚合输出）；`assets.py` 按 Source 资产扩展聚合段。

**明确不含（触界行为）:** 聚合的**内容质量**（替身受控产出）；**聚合质量审查形态不在本票交付**——R2.3 措辞为「可以单独接受质量审查」（非 MUST），Open Impl 16 保持开放，真实需要时另立票；跨 Source 的推理/关联（衍生层，24 票边界）。

**票内裁定:** 聚合 schema（三层各自最小字段）。

**Spec 覆盖责任:** A18；R2.1、R2.3。
