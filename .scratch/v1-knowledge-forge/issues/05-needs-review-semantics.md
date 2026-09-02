# 05 — 待复核（inconclusive）语义

**What to build（单一产品增量）:** 推理审计结论「不确定」的单元 → `needs_review`、不进发布集、运行摘要记录明确理由（无法可靠判定，非低质量兜底）；该 Source 整体 `needs_review`（存在未获最终结论的问题）。

**Spec anchors:** R4.4、R4.6、A14。

**Blocked by（硬依赖）:** None。软依赖/顺序建议：03（同一分支结构的处置先例）。

**Status:** done (2026-09-02, Codex 独立复审 READY WITH NON-BLOCKING → closure review READY / 0 blocking)

**Materialized from:** plan v2.2 票 05（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [x] 替身对某单元返回 `inconclusive` + 理由 → 发布集无该单元
- [x] run-summary 该单元 `needs_review` 且 reason 非空（断言理由文本来自替身结论，不是兜底措辞）
- [x] Source `needs_review`；其余单元不受影响

**Implementation / code anchors:** `pipeline.py` inconclusive 分支（与 03 分道：03 处理 reject，本票处理 inconclusive）；`artifacts.py` 的 needs_review 常量已备。

**明确不含（触界行为）:** 人工复核流程/界面（V1 无）；needs_review 单元是否进缺口报告（A14 只要求运行摘要——默认不进，若票内裁定要进须记录理由）。

**票内裁定:** Source `needs_review` 的构成条件初始裁定（建议：任一单元 needs_review ⇒ Source needs_review，可改）。

**Spec 覆盖责任:** A14；R4.4、R4.6；R3.8（needs_review 语义与其触发——「低可信」仅为风险信号，无独立状态值）。

> 票内裁定落定记录（2026-09-02 done）：
> - Source `needs_review` 构成条件：任一单元 needs_review ⇒ Source needs_review
>   （采纳建议初始裁定；R4.6「存在未获最终结论的问题」）；Source 级 reason
>   指名待复核单元 id（可解释）。
> - 缺口报告：needs_review 单元**不进**缺口报告（默认裁定）——A14 只要求
>   运行摘要有下落；缺口报告只记异常与缺口（裁决 6），待复核是「未决」非
>   异常；R4.6 拒绝与待复核不混用（audit_rejection 条目只属拒绝）。
> - 优先序：inconclusive 是完整下落（不进发布集 + 摘要留痕），先于忠实性
>   程序门与无引用挡板生效（单单元单条下落，与 03 票拒绝先例一致——本票
>   「同一分支结构的处置先例」锚点即指此）；程序门只守「通过」路径。Codex
>   audit 曾提异议（High，主张程序门前置处置 inconclusive），裁定 declined：
>   与 03/04 票已复审接受的先例、本票 What 的无条件映射（不确定 →
>   needs_review）冲突，且 R3.1/A1 的 MUST（假引用不进发布集）在任何结论
>   下均保持；Codex 独立复审确认 declined 正确。
> - 守卫：inconclusive 缺（可读）理由 → fail loud（ValueError，与 03 票拒绝
>   缺理由守卫对称；理由只能来自替身结论，不容兜底措辞——A14/R4.4）；
>   结论值域外 → `InvalidAuditVerdictError`（ValueError 族，含 low_confidence：
>   R3.8「低可信」不是结论值/状态）；06 票 missing_source_reference 挡板
>   保留于通过路径。R3.8 负半面（值域守卫拒收 low_confidence）已测；正半面
>   （信号触发待复核）待真实角色信号存在后由后续票覆盖。
> - cc-suite audit 记录：`.cc-suite/audits/audit-20260902-193828-findings.md`
>   （2 High declined + 1 Medium declined，理由在案；6 项 Low/Medium 已修）。
