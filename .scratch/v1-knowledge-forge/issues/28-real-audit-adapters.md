# 28 — 真实审查角色 adapter

**What to build（单一产品增量）:** 推理审计与覆盖审计的真实模型实现接入各自 Protocol（推理审计含 Review Note 职责，按 18 票落定的归属；覆盖审计产出 21 票的量化覆盖结论形态）；以确定性 fake provider 验证契约正确性，**不承担任何确定性产品验收**。

**Spec anchors:** Testing Decisions（真实模型冒烟不进默认验收）、ADR-0006 §1（模型 SDK 为加法依赖）、R3.4（生成与审查认知责任分离——真实审查实现与替身走同一接口，责任分离不因换实现而弱化）。

**Blocked by（硬依赖）:** 18（注记职责归属已定）、21（CoverageVerdict 最终量化形态）、22（用量契约）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 23b（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] fake provider 确定性响应 → 推理审计结论（含注记职责）与覆盖审计量化结论的解析合法、错误与用量映射到 22 票计量契约
- [ ] 替身与真实实现互换运行同一接缝测试不破

**Implementation / code anchors:** `roles.py` InferenceAuditRole / CoverageAuditRole Protocol 及 21 票扩展后的 CoverageVerdict 形态。

**明确不含（触界行为）:** 提示词调优闭环；真实端到端 eval（29）。本票与 27 **无依赖关系**、可独立实施；实现时若复用 27 已落地的 fake provider 代码，属代码复用而非计划依赖。

**票内裁定:** Open Impl 11（审查侧模型与提示词初始形态、结构化输出方式）；本票自己的 fake provider 注入形态。

**Spec 覆盖责任:** Testing Decisions（adapter 契约）；R3.4（同接口互换）。
