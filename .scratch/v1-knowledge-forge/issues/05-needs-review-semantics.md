# 05 — 待复核（inconclusive）语义

**What to build（单一产品增量）:** 推理审计结论「不确定」的单元 → `needs_review`、不进发布集、运行摘要记录明确理由（无法可靠判定，非低质量兜底）；该 Source 整体 `needs_review`（存在未获最终结论的问题）。

**Spec anchors:** R4.4、R4.6、A14。

**Blocked by（硬依赖）:** None。软依赖/顺序建议：03（同一分支结构的处置先例）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 05（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 替身对某单元返回 `inconclusive` + 理由 → 发布集无该单元
- [ ] run-summary 该单元 `needs_review` 且 reason 非空（断言理由文本来自替身结论，不是兜底措辞）
- [ ] Source `needs_review`；其余单元不受影响

**Implementation / code anchors:** `pipeline.py` inconclusive 分支（与 03 分道：03 处理 reject，本票处理 inconclusive）；`artifacts.py` 的 needs_review 常量已备。

**明确不含（触界行为）:** 人工复核流程/界面（V1 无）；needs_review 单元是否进缺口报告（A14 只要求运行摘要——默认不进，若票内裁定要进须记录理由）。

**票内裁定:** Source `needs_review` 的构成条件初始裁定（建议：任一单元 needs_review ⇒ Source needs_review，可改）。

**Spec 覆盖责任:** A14；R4.4、R4.6；R3.8（needs_review 语义与其触发——「低可信」仅为风险信号，无独立状态值）。
