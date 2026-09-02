"""领域模型：输入侧（Corpus / Source / Segment）与提炼产物侧（知识单元、来源引用）。

术语严格按 CONTEXT.md。本模块是纯数据结构 + 不变量校验，不含任何 I/O。

Source Reference 的 locator 结构（Open Impl 15 的裁定，见 ADR-0006）：
V1 的 ASS 实例使用时间区间，但 locator 是一个带 ``kind`` 的开放结构，
时间区间只是 ``kind="time_range"`` 的一种取值——结构上保留非时间定位类型
（如文本位置 ``kind="text_position"``）的表达空间（R1.4 未来兼容约束，Q26）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, Union

# ---------------------------------------------------------------------------
# 输入侧：Corpus / Source / Segment
# ---------------------------------------------------------------------------

SegmentId = str


@dataclass(frozen=True)
class Segment:
    """Source 内可定位的语义片段，引用锚定的目标（CONTEXT.md：片段）。

    V1 的 Segment 直接对应 ASS 的一条 Dialogue 事件（02 票再裁定划分算法，
    Open Impl 14）。文本保留解析后的原文形态，供逐字引用程序比对。
    """

    segment_id: SegmentId
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(frozen=True)
class Source:
    """一个可以独立处理和追溯的输入单位（CONTEXT.md：来源）。

    ``segments`` 按 Source 内出现顺序排列；segment_id 在 Source 内唯一。
    时间戳不是 Source 成立的必要条件（R1.4）：``start_ms``/``end_ms`` 为
    ``None`` 表示该 Segment 无时间轴信息（V1 的 ASS 输入总是有，但模型
    结构不锁死）。
    """

    source_id: str
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class Corpus:
    """一批相关输入组成的集合（CONTEXT.md：语料集）。批处理的单位。"""

    sources: tuple[Source, ...]


# ---------------------------------------------------------------------------
# 提炼产物侧：Source Reference / Knowledge Unit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeRangeLocator:
    """时间区间定位：ASS 等带时间轴输入的 locator（R1.4 V1 验收形态）。"""

    kind: Literal["time_range"] = "time_range"
    start_ms: int = 0
    end_ms: int = 0


@dataclass(frozen=True)
class TextPositionLocator:
    """文本位置定位：无时间轴输入的 locator（R1.4 未来兼容，V1 不验收）。"""

    kind: Literal["text_position"] = "text_position"
    segment_id: SegmentId = ""
    char_start: int = 0
    char_end: int = 0


# locator 是开放 union：新增定位类型只增不改，时间区间不是必填语义的
# 一部分（Q26——定位信息的表达不把时间区间设为必填）。
Locator = Annotated[
    Union[TimeRangeLocator, TextPositionLocator],
    "开放定位类型 union；新增类型只增不改",
]


@dataclass(frozen=True)
class SourceReference:
    """知识单元到原文的追溯锚点（CONTEXT.md：来源引用）。

    = 原文文本片段（quoted_text）+ 定位信息（locator）。
    知识单元审计与可信发布集准入的最小凭据（R2.4）。
    """

    segment_id: SegmentId
    quoted_text: str
    locator: Locator = field(default_factory=TimeRangeLocator)


# 知识单元类型不限于 Claim（R2.2、ADR-0001）：方法、解释、案例、论证、
# 结论等具有独立知识含义的表达。类型集合开放——新增类型只增不改。
UnitType = Literal["claim", "method", "explanation", "case", "argument", "conclusion"]


@dataclass(frozen=True)
class KnowledgeUnit:
    """知识资产中可被独立引用、审计、接受、拒绝或待复核的基础语义产物
    单位（CONTEXT.md：知识单元）。"""

    unit_id: str
    unit_type: UnitType
    statement: str
    source_reference: SourceReference | None
    # 提炼阶段可发现疑点，但只是信号，不构成正式 Review Note（裁决 4）。
    # 正式 Review Note 由审查环节确认并产出（09 票）。
    extraction_doubts: tuple[str, ...] = ()
