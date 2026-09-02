"""管线：单 Source 端到端执行（解析 → 提炼 → 审查 → 发布/对账）。

Q27 裁决：具体阶段拓扑不是产品强制架构，本模块的内部函数划分也不对
外承诺。外部接缝只是：输入（Corpus + 认知角色集）→ 运行结果
（可信发布集、缺口报告、运行摘要 + 按 Source 的候选单元，供资产落盘）。

本票（03）的行为范围：推理审计结论为"拒绝"的候选单元不进可信发布集，
缺口报告留 audit_rejection 条目（含 Source、指向单元、原因、下落），
运行摘要记 rejected——含被拒单元的 Source 仍为 success（A4：全部单元
有明确下落即成功）。待复核（inconclusive）与无引用单元的下落语义仍
由后续票落地——本票对这些路径显式挡住（fail loud），不做半成品处理，
避免静默产出语义错误的产物。

角色行为的可观察性（Testing Decisions：替身分别设定行为，断言只针对
外部产物）：提炼行为体现在可信发布集内容；推理审计的结论理由（通过/
拒绝）记录进运行摘要，拒绝另留缺口条目；覆盖审计结论记录进运行
摘要——三个认知角色的行为变化都无需窥探内部即可辨别。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .artifacts import (
    GAP_AUDIT_REJECTION,
    GAP_OUTCOME_AUDIT_REJECTION,
    SOURCE_STATUS_SUCCESS,
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

        # —— 单元级审查（独立认知责任，R3.4）——
        units_record: list[UnitRecord] = []
        for unit in extraction.units:
            verdict = roles.inference_auditor.audit_unit(source, unit)

            if verdict.verdict == "reject":
                # 票内裁定（优先序）：审计拒绝是完整下落——被拒单元不进
                # 发布集（R2.4 已满足）且留痕（A11），故拒绝先于无引用挡板
                # 生效；missing_source_reference 挡板只守"通过"路径。
                if not verdict.reason:
                    # A11：缺口条目须含原因。拒绝结论不带理由是角色契约
                    # 破坏，fail loud，不产出缺原因的半成品条目。
                    raise ValueError(
                        f"推理审计对知识单元 {unit.unit_id!r} 返回拒绝结论但缺少理由："
                        "缺口报告条目须含原因（A11）"
                    )
                # 审计拒绝的下落（R3.5、R4.2，A2/A4）：不进可信发布集；
                # 缺口报告留 audit_rejection 条目（Source、指向单元、
                # 原因、下落——A11）；运行摘要记 rejected。被拒单元有
                # 明确下落，不妨碍 Source 成功（R4.6：拒绝只发生在
                # Knowledge Unit 级，Source 级无"拒绝"）。
                gaps.append(
                    GapEntry(
                        category=GAP_AUDIT_REJECTION,
                        source_id=source.source_id,
                        subject=unit.unit_id,
                        reason=verdict.reason,
                        outcome=GAP_OUTCOME_AUDIT_REJECTION,
                    )
                )
                units_record.append(
                    UnitRecord(
                        unit_id=unit.unit_id, status=UNIT_STATUS_REJECTED, reason=verdict.reason
                    )
                )
                continue

            if verdict.verdict != "pass":
                # 待复核（inconclusive）的严格语义（R4.4：无法可靠判定，
                # 非低质量兜底）由后续票落地；本票显式挡住，不产出语义
                # 错误的产物。
                raise OutOfScopeVerdictError(unit.unit_id, verdict.verdict)
            if unit.source_reference is None:
                # R2.4：无有效 Source Reference 不得进入发布集，且须有
                # 显性下落——该下落的完整语义（R2.4、A17）由后续票落地。
                raise OutOfScopeVerdictError(unit.unit_id, "missing_source_reference")

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

        source_records.append(
            SourceRecord(
                source_id=source.source_id,
                status=SOURCE_STATUS_SUCCESS,
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


class OutOfScopeVerdictError(NotImplementedError):
    """审计拒绝之外仍未实现下落路径的显式挡板（fail loud，不静默降级）。"""

    def __init__(self, unit_id: str, verdict: str):
        super().__init__(
            f"知识单元 {unit_id!r} 走入未实现的下落路径（{verdict!r}）："
            "待复核（R4.4）与无引用（R2.4）单元的完整下落语义由后续票落地"
        )
