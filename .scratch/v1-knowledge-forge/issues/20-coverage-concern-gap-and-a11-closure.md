# 20 — 覆盖存疑缺口（A11 收口票）

**What to build（单一产品增量）:** 覆盖审计结论为「遗漏」时，缺口报告出现 `coverage_concern` 条目；该结论只能来自审查环节（提炼自评良好不影响条目来源）。**本票同时收口 A11**：四类缺口条目的完整字段与双读形态做总验收。

**Spec anchors:** R3.3、R4.2、A15、A11（收口）。

**Blocked by（硬依赖）:** 03、07、08（均硬——A11 收口断言需要三类真实条目已存在，本票必须在三者之后实施以单 session 完成验收；04 非依赖：03 已提供真实 audit_rejection 条目）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 17（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 提炼替身自评覆盖良好 + 覆盖审计替身判遗漏 → gap-report `coverage_concern` 条目（含 source_id、理由、outcome）
- [ ] 仅提炼自评信号、审计良好 → 无条目
- [ ] **A11 收口断言**：一个集成场景（或分场景）使四类条目（03/04 审计拒绝、07 执行失败、08 警告、本票覆盖存疑）同时具备真实条目，断言每条含 `category/source_id/subject/reason/outcome` 全字段、人可读文字与机可解析结构并存

**Implementation / code anchors:** `pipeline.py` 覆盖审计结论处（Ticket 01 已进运行摘要，缺缺口条目）；`StubCoverageAuditor` 已可预设。

**明确不含（触界行为）:** 覆盖指标形态（21 票）；覆盖结论对发布集的影响（边界显式声明：准入只由单元审计决定，ADR-0003 / Implementation Decisions 2）。

**票内裁定:** 条目 reason/outcome 措辞形态。**A11 收口责任固定在本票**（26 仅在空环境复验可读性，不承担收口）。

**Spec 覆盖责任:** A15、A11（收口）；R3.3、R4.2。
