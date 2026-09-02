"""管线：单 Source 端到端执行（解析 → 提炼 → 审查 → 发布/对账）。

Q27 裁决：具体阶段拓扑不是产品强制架构，本模块的内部函数划分也不对
外承诺。外部接缝只是：输入（Corpus + 认知角色集）→ 运行结果
（可信发布集、缺口报告、运行摘要 + 按 Source 的候选单元，供资产落盘）。

审计门 = **程序比对 ∧ 推理审计** 双通过（04 票，A1 / Impl 2）：
- 程序比对（R3.1）：发布集准入前的程序门——quoted_text 无法在所指
  Segment 原文中比对成立的单元不进可信发布集，以 audit_rejection 落
  缺口报告。不经任何认知角色（Impl 5：忠实性审计含纯程序比对部分，
  不由生成同一内容的替身自评）。
- 推理审计（03 票）：替身结论为"拒绝"的单元不进发布集，缺口报告留
  audit_rejection 条目（含 Source、指向单元、原因、下落），运行摘要
  记 rejected。

三类拒绝共用同一拒绝下落机制（03 票）：推理审计拒绝、忠实性程序比对
拒绝（04 票）、无引用门拒绝（06 票），reason 前缀可辨来源。含被拒单元
（含无引用单元）的 Source 仍为 success（A4：全部单元有明确下落即成功）。

待复核（inconclusive，05 票）：推理审计结论"不确定"的单元是**未决**
而非异常——单元记 needs_review、不进发布集（无法可靠判定 ⇒ 不得
放行），运行摘要记录来自替身结论的明确理由（R4.4 严格语义：无法
可靠判定，非低质量兜底；A14）；不进缺口报告（票内裁定：A14 只要求
运行摘要有下落，缺口报告只记异常与缺口，且 R4.6 要求拒绝与待复核
不混用）。任一单元 needs_review ⇒ 该 Source 整体 needs_review
（R4.6：存在未获最终结论、需后续人工或系统判断的问题）。

无引用门（06 票，R2.4、A17）：推理审计通过但无有效 Source Reference
的单元不进可信发布集，以审计拒绝下落（票内裁定：rejected +
audit_rejection——准入凭据缺失是准入问题而非执行失败，与 04 票程序门
同族；Spec Impl 2 / ADR-0003）。明确不含：引用有效性分级体系不建——
None 是唯一「无引用」形态，非 None 的引用缺陷（空引用 / segment 不存在
/ 引用不在原文）由 04 票忠实性程序门处置；locator 校验不展开。

角色行为的可观察性（Testing Decisions：替身分别设定行为，断言只针对
外部产物）：提炼行为体现在可信发布集内容；推理审计的结论理由（通过/
拒绝/待复核）记录进运行摘要，拒绝另留缺口条目；覆盖审计结论记录进
运行摘要——三个认知角色的行为变化都无需窥探内部即可辨别。程序门的结论
（忠实性比对成立与否）不经认知角色，直接以同一下落机制可观察。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .artifacts import (
    GAP_AUDIT_REJECTION,
    GAP_OUTCOME_AUDIT_REJECTION,
    SOURCE_STATUS_NEEDS_REVIEW,
    SOURCE_STATUS_SUCCESS,
    UNIT_STATUS_NEEDS_REVIEW,
    UNIT_STATUS_PASSED,
    UNIT_STATUS_REJECTED,
    GapEntry,
    GapReport,
    RunSummary,
    SourceRecord,
    TrustedSet,
    TrustedSetEntry,
    UnitRecord,
)
from .model import Corpus, KnowledgeUnit, Source
from .roles import CognitiveRoles


@dataclass(frozen=True)
class RunOutcome:
    """一次端到端运行的全部结果（三类外部产物 + 落盘所需的候选单元）。

    ``source_units`` 是内部传递结构（不属外部产物）：按 Source 组织的
    候选知识单元，资产落盘由此取材，避免对认知角色的二次调用。
    """

    trusted_set: TrustedSet
    gap_report: GapReport
    run_summary: RunSummary
    source_units: dict[str, tuple[KnowledgeUnit, ...]] = field(default_factory=dict)


def _locator_dict(unit: KnowledgeUnit) -> dict:
    locator = unit.source_reference.locator
    return {"kind": locator.kind, **{k: v for k, v in locator.__dict__.items() if k != "kind"}}


def _trusted_entry(source: Source, unit: KnowledgeUnit) -> TrustedSetEntry:
    ref = unit.source_reference
    assert ref is not None  # 调用方已保证（R2.4：无引用单元不进发布集）
    return TrustedSetEntry(
        source_id=source.source_id,
        unit_id=unit.unit_id,
        unit_type=unit.unit_type,
        statement=unit.statement,
        segment_id=ref.segment_id,
        quoted_text=ref.quoted_text,
        locator=_locator_dict(unit),
    )


def _reject_unit(
    source: Source,
    unit: KnowledgeUnit,
    reason: str,
    gaps: list[GapEntry],
    units_record: list[UnitRecord],
) -> None:
    """审计拒绝的统一下落（03 票机制，R3.5、R4.2，A2/A4/A11）：被拒单元
    不进可信发布集（R2.4 已满足）；缺口报告留 audit_rejection 条目
    （Source、指向单元、原因、下落——A11）；运行摘要记 rejected。三类
    拒绝共用本机制，reason 可辨来源：推理审计拒绝（03 票）、忠实性程序
    比对拒绝（04 票）、无引用门拒绝（06 票）。"""

    gaps.append(
        GapEntry(
            category=GAP_AUDIT_REJECTION,
            source_id=source.source_id,
            subject=unit.unit_id,
            reason=reason,
            outcome=GAP_OUTCOME_AUDIT_REJECTION,
        )
    )
    units_record.append(
        UnitRecord(unit_id=unit.unit_id, status=UNIT_STATUS_REJECTED, reason=reason)
    )


# 忠实性比对的最小规范化（Open Impl 10 票内裁定）：任意空白连续段——
# 空格、换行（ASS \N 解析后的形态）、制表等——折叠为单个空格，去首尾
# 空白。只容忍排版差异；非空白字符的增删改一概不放过（逐字性保持）。
# 全半角折叠、大小写、Unicode 规范形态等属比对容差的真实数据调优，
# 不在本票范围。
_WHITESPACE_RUN_RE = re.compile(r"\s+")

# 忠实性拒绝理由的稳定前缀：缺口条目与运行摘要据此可辨原因来自忠实性
# 程序比对（区别于推理审计的拒绝）。
_FAITHFULNESS_REASON_PREFIX = "忠实性比对不成立"

# 无引用拒绝理由的稳定前缀（06 票）：缺口条目与运行摘要据此可辨原因
# 来自 R2.4 无引用门（区别于推理审计与忠实性程序比对两类拒绝）。
_MISSING_REFERENCE_REASON_PREFIX = "无来源引用"


def _normalize_for_quote_match(text: str) -> str:
    """最小规范化：空白连续段折叠为单个空格，去首尾空白。"""

    return _WHITESPACE_RUN_RE.sub(" ", text).strip()


def _faithfulness_rejection_reason(
    normalized_segments: dict[str, str], unit: KnowledgeUnit
) -> str | None:
    """忠实性程序比对（R3.1、A1）：quoted_text 必须能在所指 Segment 的
    原文中比对成立（Segment.text 为比对基准）。

    ``normalized_segments`` 是按 segment_id 索引的最小规范化原文（每个
    Source 构建一次）。返回 None 表示成立；否则返回以
    _FAITHFULNESS_REASON_PREFIX 开头的拒绝理由。纯程序比对，不经任何
    认知角色（Impl 5）。比对成立 = 最小规范化后的引用文本是所指片段
    规范化原文的逐字子串；空引用文本不构成逐字引用（空串是任意文本的
    子串，不得因此空洞成立）。
    """

    ref = unit.source_reference
    assert ref is not None  # 调用方已处置无引用单元（06 票无引用门在前）
    quote = _normalize_for_quote_match(ref.quoted_text)
    if not quote:
        return f"{_FAITHFULNESS_REASON_PREFIX}：引用文本为空，不构成逐字引用"
    segment_text = normalized_segments.get(ref.segment_id)
    if segment_text is None:
        return f"{_FAITHFULNESS_REASON_PREFIX}：所指片段 {ref.segment_id} 不存在于该 Source 的原文"
    if quote not in segment_text:
        return f"{_FAITHFULNESS_REASON_PREFIX}：引用文本不存在于所指片段 {ref.segment_id} 的原文"
    return None


def run_corpus(corpus: Corpus, roles: CognitiveRoles) -> RunOutcome:
    """对一个 Corpus 执行端到端流程。

    每个认知角色对每个作用对象恰好调用一次。本次运行（01 骨架）产出
    的对账覆盖 Corpus 全量 Source 及其全部知识单元。
    """

    started = time.monotonic()
    trusted: list[TrustedSetEntry] = []
    gaps: list[GapEntry] = []
    source_records: list[SourceRecord] = []
    source_units: dict[str, tuple[KnowledgeUnit, ...]] = {}

    for source in corpus.sources:
        # —— 提炼（生成认知责任）——
        extraction = roles.extractor.extract(source)
        source_units[source.source_id] = extraction.units

        # 忠实性比对基准索引：每个 Segment 原文最小规范化恰一次，单元
        # 程序门按 segment_id 直接查找（比对基准是所指 Segment 的原文）。
        normalized_segments = {
            s.segment_id: _normalize_for_quote_match(s.text) for s in source.segments
        }

        # —— 单元级审查（独立认知责任，R3.4）——
        units_record: list[UnitRecord] = []
        for unit in extraction.units:
            verdict = roles.inference_auditor.audit_unit(source, unit)

            if verdict.verdict == "reject":
                # 票内裁定（优先序）：审计拒绝是完整下落——被拒单元不进
                # 发布集（R2.4 已满足）且留痕（A11），故拒绝先于忠实性
                # 程序门与无引用门生效（单单元单条下落）；后两者只守
                # "通过"路径。
                if not verdict.reason.strip():
                    # A11：缺口条目须含原因。拒绝结论不带（可读）理由是
                    # 角色契约破坏，fail loud，不产出缺原因的半成品条目。
                    raise ValueError(
                        f"推理审计对知识单元 {unit.unit_id!r} 返回拒绝结论但缺少理由："
                        "缺口报告条目须含原因（A11）"
                    )
                _reject_unit(source, unit, verdict.reason, gaps, units_record)
                continue

            if verdict.verdict == "inconclusive":
                # 待复核下落（05 票机制，R4.4、R4.6、A14）："不确定"的
                # 单元是未决而非异常——不进可信发布集（无法可靠判定 ⇒
                # 不得放行），运行摘要记 needs_review，理由取自推理审计
                # 结论本身（R4.4 严格语义的来源要求：理由是替身"为什么
                # 无法判定"的陈述，不是系统对质量的兜底评语）。
                # 票内裁定：不留缺口条目——A14 只要求运行摘要有下落，
                # 缺口报告只记异常与缺口（裁决 6），待复核是"未决"而非
                # 异常，且 R4.6 要求拒绝与待复核不混用。
                # 票内裁定（优先序，与 03 票拒绝先例一致）：待复核是
                # 完整下落，先于忠实性程序门与无引用门生效（单单元
                # 单条下落）；对未决单元跑程序门只会制造第二条下落
                # （拒绝与待复核混用，R4.6 禁止）。
                if not verdict.reason.strip():
                    # A14 / R4.4：运行摘要须记录待复核的明确理由，且理由
                    # 只能来自替身结论（不容系统兜底措辞）。不带（可读）
                    # 理由是角色契约破坏，fail loud（与 03 票拒绝缺理由
                    # 守卫对称）。
                    raise ValueError(
                        f"推理审计对知识单元 {unit.unit_id!r} 返回待复核结论但缺少理由："
                        "运行摘要须记录待复核的明确理由（A14、R4.4）"
                    )
                units_record.append(
                    UnitRecord(
                        unit_id=unit.unit_id, status=UNIT_STATUS_NEEDS_REVIEW, reason=verdict.reason
                    )
                )
                continue

            if verdict.verdict != "pass":
                # 结论值域守卫（fail loud）：pass/reject/inconclusive 之外
                # 的结论值是角色契约破坏（"低可信"只是风险信号，不是
                # 结论值，R3.8），不得静默当作任何已知下落处置。
                raise InvalidAuditVerdictError(unit.unit_id, verdict.verdict)
            if unit.source_reference is None:
                # —— 无引用门（06 票，R2.4、A17）——
                # 推理审计通过但无有效 Source Reference 的单元不进可信
                # 发布集：Source Reference 是准入凭据（引用文本 + 定位，
                # R2.4），缺失即拒绝。票内裁定：实体状态 rejected、Gap
                # Category audit_rejection——无引用单元的提炼与审查流程
                # 完整走完，缺陷在准入凭据而非执行（非 execution_failure），
                # 属准入性拒绝（与 04 票程序门同族，Spec Impl 2 /
                # ADR-0003），经 03 票统一下落机制留痕。优先序：晚于推理
                # 审计结论处置（03/05 票先例），先于忠实性程序门——无引用
                # 即无可比对文本，忠实性比对不适用。
                _reject_unit(
                    source,
                    unit,
                    f"{_MISSING_REFERENCE_REASON_PREFIX}：知识单元缺少 Source "
                    "Reference，不构成可信发布集的准入凭据",
                    gaps,
                    units_record,
                )
                continue

            # —— 忠实性程序比对（发布集准入前的程序门，R3.1、A1）——
            # 审计门 = 程序比对 ∧ 推理审计：推理审计通过不足以放行——
            # quoted_text 无法在所指 Segment 原文比对成立的单元同样拒绝，
            # 经同一拒绝下落机制（03 票）。不经任何认知角色（Impl 5）。
            faithfulness_reason = _faithfulness_rejection_reason(normalized_segments, unit)
            if faithfulness_reason is not None:
                _reject_unit(source, unit, faithfulness_reason, gaps, units_record)
                continue

            trusted.append(_trusted_entry(source, unit))
            # 通过结论的理由进运行摘要：推理审计角色的行为在外部产物中
            # 可辨（Testing Decisions），也是单元下落的一部分。
            units_record.append(
                UnitRecord(unit_id=unit.unit_id, status=UNIT_STATUS_PASSED, reason=verdict.reason)
            )

        # —— 覆盖审计（独立审查环节，裁决 3）——
        coverage = roles.coverage_auditor.audit_coverage(source, list(extraction.units))
        # 覆盖结论进运行摘要（可观察通道）；"覆盖存疑"缺口条目（R4.2
        # 缺口类别）与指标成对（ADR-0003）由后续票落地。

        # —— Source 级实体状态（R4.6 可观察语义）——
        # 票内裁定（05 票初始裁定）：任一单元 needs_review ⇒ Source
        # needs_review（存在未获最终结论、需后续人工或系统判断的问题，
        # 尚不能视为完全 settled）。被拒单元是已决下落，不妨碍 success
        # （A4）；Source 失败（07 票）是流程未完整完成，另属失败路径。
        pending_review_unit_ids = [
            u.unit_id for u in units_record if u.status == UNIT_STATUS_NEEDS_REVIEW
        ]
        if pending_review_unit_ids:
            source_status = SOURCE_STATUS_NEEDS_REVIEW
            source_reason = f"存在未获最终结论的待复核单元：{'、'.join(pending_review_unit_ids)}"
        else:
            source_status = SOURCE_STATUS_SUCCESS
            source_reason = ""

        source_records.append(
            SourceRecord(
                source_id=source.source_id,
                status=source_status,
                reason=source_reason,
                units=tuple(units_record),
                coverage=coverage,
            )
        )

    summary = RunSummary(
        sources=tuple(source_records),
        wall_time_ms=int((time.monotonic() - started) * 1000),
    )
    return RunOutcome(
        trusted_set=TrustedSet(entries=tuple(trusted)),
        gap_report=GapReport(entries=tuple(gaps)),
        run_summary=summary,
        source_units=source_units,
    )


class InvalidAuditVerdictError(ValueError):
    """推理审计结论值域守卫（05 票，fail loud）：pass / reject /
    inconclusive 之外的结论值是**角色契约破坏**（与缺理由守卫同族），
    不是"未建成"——"低可信"只是风险信号，不是结论值或状态（R3.8）。"""

    def __init__(self, unit_id: str, verdict: str):
        super().__init__(
            f"推理审计对知识单元 {unit_id!r} 返回值域外的结论 {verdict!r}："
            "结论值只能是 pass / reject / inconclusive"
        )
