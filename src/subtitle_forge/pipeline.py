"""管线：单 Source 端到端执行（解析 → 提炼 → 审查 → 发布/对账）。

Q27 裁决：具体阶段拓扑不是产品强制架构，本模块的内部函数划分也不对
外承诺。外部接缝只是：输入（Corpus + 认知角色集）→ 运行结果
（可信发布集、缺口报告、运行摘要 + 按 Source 的候选单元，供资产落盘）。

本票（01）的行为范围：全部候选单元经审查替身判定"通过"且带有效
Source Reference → 进入可信发布集。拒绝/不确定/无引用单元的下落语义
在 03/04 票落地——本票对这些路径显式挡住（fail loud），不做半成品
处理，避免静默产出语义错误的产物。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .artifacts import (
    SOURCE_STATUS_SUCCESS,
    UNIT_STATUS_PASSED,
    GapEntry,
    GapReport,
    RunSummary,
    SourceRecord,
    TrustedSet,
    TrustedSetEntry,
    UnitRecord,
)
from .model import Corpus, KnowledgeUnit, Source
from .roles import (
    ROLE_COVERAGE_AUDITOR,
    ROLE_EXTRACTOR,
    ROLE_INFERENCE_AUDITOR,
    CognitiveRoles,
)


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

    每个认知角色对每个作用对象恰好调用一次、独立计量（调用次数进
    运行摘要——12 票计量契约的最小雏形）。本次运行（01 骨架）产出的
    对账覆盖 Corpus 全量 Source 及其全部知识单元。
    """

    started = time.monotonic()
    role_calls = {ROLE_EXTRACTOR: 0, ROLE_INFERENCE_AUDITOR: 0, ROLE_COVERAGE_AUDITOR: 0}
    trusted: list[TrustedSetEntry] = []
    gaps: list[GapEntry] = []
    source_records: list[SourceRecord] = []
    source_units: dict[str, tuple[KnowledgeUnit, ...]] = {}

    for source in corpus.sources:
        # —— 提炼（生成认知责任）——
        extraction = roles.extractor.extract(source)
        role_calls[ROLE_EXTRACTOR] += 1
        source_units[source.source_id] = extraction.units

        # —— 单元级审查（独立认知责任，R3.4）——
        units_record: list[UnitRecord] = []
        for unit in extraction.units:
            verdict = roles.inference_auditor.audit_unit(source, unit)
            role_calls[ROLE_INFERENCE_AUDITOR] += 1

            if verdict.verdict != "pass":
                # 拒绝/不确定的完整下落语义（缺口报告"审计拒绝"、待复核）
                # 由 03/04 票落地；本票显式挡住，不产出语义错误的产物。
                raise OutOfScopeVerdictError(unit.unit_id, verdict.verdict)
            if unit.source_reference is None:
                # R2.4：无有效 Source Reference 不得进入发布集，且须有显性
                # 下落——该下落的完整语义（A17）由 03 票裁定。
                raise OutOfScopeVerdictError(unit.unit_id, "missing_source_reference")

            trusted.append(_trusted_entry(source, unit))
            units_record.append(UnitRecord(unit_id=unit.unit_id, status=UNIT_STATUS_PASSED))

        # —— 覆盖审计（独立审查环节，裁决 3）——
        coverage = roles.coverage_auditor.audit_coverage(source, list(extraction.units))
        role_calls[ROLE_COVERAGE_AUDITOR] += 1
        # 覆盖存疑 → 缺口报告"覆盖存疑"条目与指标成对由 08 票落地；本票
        # 默认覆盖良好时无条目，结构与调用通道已就位。

        source_records.append(
            SourceRecord(
                source_id=source.source_id,
                status=SOURCE_STATUS_SUCCESS,
                units=tuple(units_record),
            )
        )

    summary = RunSummary(
        sources=tuple(source_records),
        role_call_counts=dict(role_calls),
        wall_time_ms=int((time.monotonic() - started) * 1000),
    )
    return RunOutcome(
        trusted_set=TrustedSet(entries=tuple(trusted)),
        gap_report=GapReport(entries=tuple(gaps)),
        run_summary=summary,
        source_units=source_units,
    )


class OutOfScopeVerdictError(NotImplementedError):
    """01 骨架范围外路径的显式挡板（fail loud，不静默降级）。"""

    def __init__(self, unit_id: str, verdict: str):
        super().__init__(
            f"知识单元 {unit_id!r} 走入 01 骨架未实现的路径（{verdict!r}）："
            "拒绝/不确定/无引用单元的完整下落语义由 03/04 票落地"
        )
