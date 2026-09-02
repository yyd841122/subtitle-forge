# 22 — 成本与耗时可观察（确定性计量契约）

**What to build（单一产品增量）:** 运行摘要含成本与耗时记录（各认知角色调用计量、总成本、耗时），两次运行的记录可比较——**计量是确定性的，不依赖 wall-clock 或真实模型**。

**Spec anchors:** R7.1、A12、ADR-0006 §3 的计量契约预留。

**Blocked by（硬依赖）:** 09（可比较性验收使用范围运行）。（03 非依赖：角色集自 Ticket 01 起已存在。）

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 19（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 计量 fixture 确定性：替身角色每次被调用记 1 次调用 + 票内裁定的固定用量值（如 per-call `cost_units`）；运行摘要含 per-role calls / cost_units / wall_time_ms，**总成本字段非空且为确定性值**
- [ ] 可比较性：全量运行 vs 范围运行（联动 09，`--source` 单个）→ 两次记录可辨且差异反映范围（调用数与 cost_units 随 Source 数变化）；断言不依赖 wall_time 的大小关系（wall_time 记录但不作比较判据）

**Implementation / code anchors:** `CognitiveRoles` 组装处（计量包装）；`RunSummary.wall_time_ms` 已有，扩展结构化计量。

**明确不含（触界行为）:** 成本控制策略（23 票）；预算硬限制（V1 无）。

**票内裁定:** Open Impl 17 记录粒度（每角色调用数/用量字段——真实货币用量由 27/28 的 adapter 填充，本票定契约与确定性值）。

**Spec 覆盖责任:** A12（观察/比较，联动 09 控制手段）；R7.1。
