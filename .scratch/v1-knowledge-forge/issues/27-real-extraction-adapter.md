# 27 — 真实提炼角色 adapter

**What to build（单一产品增量）:** 真实模型提炼实现接入 `ExtractionRole`（同一接口与替身可互换运行）：结构化输出解析、错误映射、用量映射（填充 22 票契约的真实用量字段）。**不承担任何确定性产品验收**——契约正确性用本地 fake provider（确定性响应）验证。

**Spec anchors:** Testing Decisions（真实模型冒烟不进默认验收）、ADR-0006 §1（模型 SDK 为加法依赖）。

**Blocked by（硬依赖）:** 19（接口含聚合）、22（用量契约）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 23a（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] fake provider 确定性响应 → adapter 产出合法候选单元（含聚合输出，19 已扩展接口）与用量记录
- [ ] 替身与真实实现互换运行同一接缝测试不破

**Implementation / code anchors:** `roles.py` ExtractionRole Protocol；依赖引入按 ADR-0006 §1（模型 SDK 为加法，不推翻零依赖基线）。

**明确不含（触界行为）:** 提示词调优闭环；真实端到端 eval（29）。

**票内裁定:** Open Impl 11（模型选择与提示词**初始**形态）；fake provider 的注入形态。

**Spec 覆盖责任:** Testing Decisions（adapter 契约，不承担 A 条款验收）。
