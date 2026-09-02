# 06 — 无 Source Reference 单元的下落

**What to build（单一产品增量）:** 无有效 Source Reference 的知识单元不进可信发布集，且在运行摘要/缺口报告有显性下落（状态取值与 Gap Category 归属由票内裁定——R2.4 明示属实现决策）。

**Spec anchors:** R2.4、A17。

**Blocked by（硬依赖）:** 03。

**Status:** in_progress（2026-09-02 开工，票内裁定已落，见文末裁定记录）

**Materialized from:** plan v2.2 票 06（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 替身产出无引用单元（其余正常）→ 该单元不在发布集
- [ ] run-summary 有其记录（状态可辨、reason 提「无来源引用」）
- [ ] gap-report 有指向它的条目；Source 的最终状态与 A4 语义一致（单元有下落即不妨碍 success——若票内裁定不同须记录理由）

**Implementation / code anchors:** `pipeline.py`（Ticket 01 基线 98–101 行，`source_reference is None` 的挡板）；`model.KnowledgeUnit.source_reference` 本就可为 `None`。

**明确不含（触界行为）:** 引用有效性分级体系（如 segment_id 不存在等细分场景，票内可顺手覆盖 locator 校验但须记录，不展开体系）。

**票内裁定:** **开工即先落**无引用单元的实体状态取值（rejected/failed 之一）与 Gap Category 归属，并记入票面（验收断言按裁定后的取值表达）。

**Spec 覆盖责任:** A17；R2.4。

> 票内裁定落定记录（2026-09-02 开工即落）：
> - **实体状态取值：`rejected`**。R4.6 的「失败」一族语义是处理流程无法
>   完整完成；无引用单元的提炼与审查流程完整走完，缺陷在**准入凭据**
>   （Source Reference = 引用文本 + 定位，R2.4）而非执行。Spec
>   Implementation Decision 2 把 R2.4 与审计门语义并列（ADR-0003）；
>   04 票先例：非认知角色的程序性准入门（忠实性比对）拒绝即 `rejected`。
>   无引用门是同族第三类准入性拒绝（推理审计拒绝 / 忠实性程序门拒绝 /
>   无引用门拒绝），共用 03 票统一下落机制。
> - **Gap Category：`audit_rejection`**。四类中非 execution_failure（无执行
>   失败发生）、非 coverage_concern、非 warning（实质性排除，非提示）。
>   reason 以稳定前缀「无来源引用」开头，三类拒绝来源在外部产物中可辨。
> - **Source 级状态：`success`**（A4 默认路径，不偏离——已决下落不妨碍
>   成功；亦不触发 needs_review：rejected 是已决结论，非未决问题）。
> - **优先序**：推理审计结论处置（reject → 拒绝下落 / inconclusive →
>   待复核下落）先于无引用门（03/05 票先例，单单元单条下落）；无引用门
>   先于忠实性程序门（无引用即无可比对文本，忠实性比对不适用）。
> - **明确不含的边界记录**：引用有效性分级体系不建。`source_reference
>   is None` 是本票唯一处置的「无引用」形态；非 None 的引用缺陷（引用
>   文本为空 / segment_id 不存在 / 引用文本不在所指片段原文）仍由 04 票
>   忠实性程序门以各自拒绝理由处置——两类下落以 reason 前缀可辨。
>   **locator 校验不展开**（不实现 locator 有效性判定，留给未来的有效性
>   分级工作）。
