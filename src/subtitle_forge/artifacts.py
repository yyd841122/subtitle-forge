"""外部产物：可信发布集、缺口报告、运行摘要的规范形态（Open Impl 7 初始形态）。

每个产物都是"一份 Markdown，人直接可读；结构内嵌于代码块，机器可程序化
解析"——人读为主 + 结构内嵌（ADR-0006 裁定；终裁与迁移属 25 票）。

产物是**值结构**：管线构造它们，`assets.py` 只负责落盘为规范文件。
时间等运行元数据不进入结构本体（调用方注入），保证产物内容可比对。
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import KnowledgeUnit, Source
from .roles import CoverageVerdict

# ---------------------------------------------------------------------------
# 枚举（值域来自 CONTEXT.md / R4.6，只定义可观察语义）
# ---------------------------------------------------------------------------

# Source 级实体状态：成功/失败/待复核（无"拒绝"，A4）。
SOURCE_STATUS_SUCCESS = "success"
SOURCE_STATUS_FAILED = "failed"
SOURCE_STATUS_NEEDS_REVIEW = "needs_review"

# Knowledge Unit 级实体状态：通过/拒绝/待复核/失败（"拒绝"仅此一级）。
UNIT_STATUS_PASSED = "passed"
UNIT_STATUS_REJECTED = "rejected"
UNIT_STATUS_NEEDS_REVIEW = "needs_review"
UNIT_STATUS_FAILED = "failed"

# 缺口类别（Gap Category，不是实体状态）：执行失败/审计拒绝/覆盖存疑/警告。
GAP_EXECUTION_FAILURE = "execution_failure"
GAP_AUDIT_REJECTION = "audit_rejection"
GAP_COVERAGE_CONCERN = "coverage_concern"
GAP_WARNING = "warning"

GAP_CATEGORIES = (
    GAP_EXECUTION_FAILURE,
    GAP_AUDIT_REJECTION,
    GAP_COVERAGE_CONCERN,
    GAP_WARNING,
)

# 审计拒绝条目的下落措辞（票 03 票内裁定）：被拒单元不进发布集，但
# 在缺口报告与运行摘要中显性留痕（A11：下落可观察、可对账）。
GAP_OUTCOME_AUDIT_REJECTION = "不进入发布集，记录在案"


# ---------------------------------------------------------------------------
# 可信发布集（Trusted Set）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrustedSetEntry:
    """发布集内一个知识单元的可观察记录。

    R2.4：无有效 Source Reference 的单元不得进入——发布集条目总是带
    引用（quoted_text + locator），这是准入凭据的一部分。
    """

    source_id: str
    unit_id: str
    unit_type: str
    statement: str
    segment_id: str
    quoted_text: str
    locator: dict


@dataclass(frozen=True)
class TrustedSet:
    """可信发布集：由审计通过的知识单元组成的部分（ADR-0003 审计门）。"""

    entries: tuple[TrustedSetEntry, ...] = ()


# ---------------------------------------------------------------------------
# 缺口报告（Gap Report）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GapEntry:
    """一条缺口：四类之一，指向实体，含原因与下落（A11：人可读 + 机可解析）。"""

    category: str  # GAP_* 之一
    source_id: str
    subject: str  # 缺口指向的实体（如 unit_id，或 source 级则为 source_id）
    reason: str
    outcome: str  # 下落：该实体/问题当前的去向说明


@dataclass(frozen=True)
class GapReport:
    """缺口报告：一等资产，只记录异常与缺口，不承担全量正常对账（裁决 6）。

    本次运行无异常时内容为空、结构完整（Ticket 01：结构成立）。
    """

    entries: tuple[GapEntry, ...] = ()

    def as_list(self) -> list[GapEntry]:
        return list(self.entries)


# ---------------------------------------------------------------------------
# 运行摘要（Run Summary）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UnitRecord:
    """运行摘要中一个知识单元的去向记录（实体状态 + 理由）。"""

    unit_id: str
    status: str  # UNIT_STATUS_* 之一
    reason: str = ""


@dataclass(frozen=True)
class SourceRecord:
    """运行摘要中一个 Source 的去向记录（实体状态 + 其单元的下落）。

    ``coverage``：覆盖审计结论（独立审查环节，裁决 3）在运行摘要中的
    可观察通道——记录其结论与理由；覆盖存疑的缺口条目（R4.2 缺口
    类别）与指标成对（ADR-0003）由后续票落地。
    """

    source_id: str
    status: str  # SOURCE_STATUS_* 之一
    reason: str = ""
    units: tuple[UnitRecord, ...] = ()
    coverage: CoverageVerdict | None = None


@dataclass(frozen=True)
class RunSummary:
    """运行摘要：一次运行的全量去向对账载体（裁决 6）。

    对账作用域：本次运行涉及的 Corpus 全量 Source 与其全部知识单元
    （R4.3 把作用域升级为"当前资产版本内全量实体"，后续票落地），
    无静默消失；成本与耗时的可观察记录是其组成部分（A12、R7.1，
    计量契约由后续票展开）。
    """

    sources: tuple[SourceRecord, ...] = ()
    wall_time_ms: int | None = None

    def unit_count(self) -> int:
        return sum(len(r.units) for r in self.sources)

    def unit_records(self) -> list[UnitRecord]:
        return [u for r in self.sources for u in r.units]
