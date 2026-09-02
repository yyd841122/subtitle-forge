# 06 — 无 Source Reference 单元的下落

**What to build（单一产品增量）:** 无有效 Source Reference 的知识单元不进可信发布集，且在运行摘要/缺口报告有显性下落（状态取值与 Gap Category 归属由票内裁定——R2.4 明示属实现决策）。

**Spec anchors:** R2.4、A17。

**Blocked by（硬依赖）:** 03。

**Status:** done (2026-09-02, Codex 独立复审 READY WITH NON-BLOCKING（0 blocking）→ closure review READY / 0 blocking)

**Materialized from:** plan v2.2 票 06（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [x] 替身产出无引用单元（其余正常）→ 该单元不在发布集
- [x] run-summary 有其记录（状态可辨、reason 提「无来源引用」）
- [x] gap-report 有指向它的条目；Source 的最终状态与 A4 语义一致（单元有下落即不妨碍 success——若票内裁定不同须记录理由）

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

> 完成记录（2026-09-02 done）：
> - 实现：`pipeline.py` 无引用门（通过路径，`_reject_unit` 统一机制，
>   reason 稳定前缀「无来源引用」）；`OutOfScopeVerdictError` 挡板随
>   下落语义落地退役（无残留引用）；03/05 票的优先序裁定不变（verdict
>   处置先行），04 票界线测试改写为门间界线断言。
> - 测试：`tests/test_missing_reference_disposition.py`（9 项：验收 3 +
>   行为 4 + 触界 2）；conftest 增 `make_units_a17_no_reference` 与共享
>   `run_cli_with_roles`。全量 67 项通过。
> - cc-suite audit（full，gpt-5.6-sol/high）：0 Critical / 0 High /
>   1 Medium / 2 Low，3/3 已修——03 票优先序测试补 reason 断言（06
>   落地后两路径外部形态收敛，reason 是唯一可辨差异）、`_reject_unit`
>   docstring 三类拒绝同步、替身注册管线上移 conftest 去重。
>   记录：`.cc-suite/audits/audit-20260902-ticket06-findings.md`。
> - Codex 独立复审：READY WITH NON-BLOCKING（0 blocking，checklist A–F
>   全过——验收满足、裁定与 Spec/ADR-0003/03-04-05 先例一致、未越界、
>   挡板退役完整、测试质量合格、无正确性缺陷）；唯一 non-blocking
>   （run-summary 单元记录转字典会掩盖重复下落）已修（列表基数 +
>   unit_id 唯一性断言先行）；focused closure review：**READY / 0
>   blocking**。review thread：01a0620a-def4-7442-a948-4ef1099154ed。
