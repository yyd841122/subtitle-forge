# 03 — 审计拒绝的下落（单元级拒绝成立）

**What to build（单一产品增量）:** 推理审计结论为「拒绝」的知识单元不进可信发布集；缺口报告出现 `audit_rejection` 条目（含 Source、指向单元、原因、下落）；运行摘要该单元 `rejected`；**含被拒单元的 Source 仍为 `success`**（全部单元有明确下落即成功，A4 语义）。

**Spec anchors:** R3.5、R4.2、A2、A4、A11（audit_rejection 部分）。

**Blocked by（硬依赖）:** None（与 02 可并行）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 03（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] fixture 按 A2 场景构造——单元带真实存在于原文的引用 + 明显越界的陈述（如引用只讲基准情形、断言却推广到全部递归），推理审查替身因此对该 unit_id 预设 `reject` + 理由 → 发布集无该单元
- [ ] gap-report 含 `{category: audit_rejection, source_id, subject: unit_id, reason, outcome}`
- [ ] run-summary 该单元 `rejected`；Source `success`；同 Source 其余单元不受影响

**Implementation / code anchors:** `pipeline.py`（Ticket 01 基线 94–97 行，`verdict != "pass"` 的 `OutOfScopeVerdictError` 分支）；`StubInferenceAuditor` 已支持按 unit 预设结论。

**明确不含（触界行为）:** 忠实性程序比对（假引用场景，04 票——本票替身拒绝是唯一拒绝来源）；待复核（05 票，`inconclusive` 分支继续 fail loud）；无引用单元（06 票，`missing_source_reference` 挡板保留）。

**票内裁定:** 拒绝条目 `outcome` 字段的可观察措辞（如「不进入发布集，记录在案」）。

**Spec 覆盖责任:** A2、A4（success 含被拒单元）、A11（audit_rejection 条目）；R3.5、R4.2。

> 保留与 04 的分拆：03 是处置分支、04 是新程序组件，两个独立的 How 决策不绑定一张票。
