# 29 — 真实模型端到端 eval（非门禁）

**What to build（单一产品增量）:** 可选的真实模型端到端 eval/冒烟：保存输入、模型标识、提示词版本与观测结果；验证真实 AI 环节的接线与内容质量趋势。**不进默认验收，失败不等于确定性回归。**

**Spec anchors:** Testing Decisions（真实模型冒烟）、R1.3（知识质量观察——非 A13 验收）。

**Blocked by（硬依赖）:** 27、28。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 23c（ADR-0007）

**Acceptance:**
- [ ] 手动/标记触发一次真实模型运行 → 产出可保存、可对比的观测记录（含噪声场景的知识单元观察）
- [ ] 默认测试套件不含本票测试

**Implementation / code anchors:** 27/28 的真实实现；运行入口的可选开关。

**明确不含（触界行为）:** 作为任何 A 条款的验收依据（A13 的验收声明只在 08）。

**票内裁定:** eval 记录形态与触发方式（环境变量/标记）。

**Spec 覆盖责任:** Testing Decisions（非门禁冒烟）；R1.3（观察通道，非验收）。
