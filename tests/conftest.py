"""共享 fixture：受控 ASS Source 与按认知角色独立注入的确定性替身。

测试输入的一部分（Testing Decisions）：替身按认知角色分别注入、分别
设定行为。断言只针对外部产物。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from subtitle_forge.model import (
    KnowledgeUnit,
    SourceReference,
    TextPositionLocator,
    TimeRangeLocator,
)

# 一集"课程"的受控 ASS 内容：三条知识性 Dialogue（覆盖 claim / method /
# conclusion 三种知识单元类型，证明 R2.2 类型不限于 Claim）。
ASS_CONTENT = """[Script Info]
Title: 受控课程 01
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:06.00,Default,,0,0,0,,递归的核心结构是函数调用自身并逐步缩小问题规模
Dialogue: 0,0:00:07.50,0:00:13.20,Default,,0,0,0,,求解阶乘时先写基准情形 n 等于零返回一{\\an8}再递归调用自身
Dialogue: 0,0:00:14.00,0:00:18.30,Default,,0,0,0,,因此递归深度必须有限否则栈会溢出
"""

# 受控课程 02 的 ASS 内容（与 ep01 主题不同：动态规划）。段文本与知识
# 单元均独立于 ep01——多 Source 批处理"互不污染"的受控输入（票 02）。
ASS_CONTENT_EP02 = """[Script Info]
Title: 受控课程 02
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.50,Default,,0,0,0,,动态规划把原问题分解为重叠子问题并缓存其解
Dialogue: 0,0:00:06.00,0:00:11.80,Default,,0,0,0,,斐波那契数列是重叠子问题的经典例子{\\an8}朴素递归会重复计算
Dialogue: 0,0:00:12.40,0:00:17.00,Default,,0,0,0,,因此自底向上填表可将时间复杂度降为线性
"""

EP02_SEG_TEXTS = [
    "动态规划把原问题分解为重叠子问题并缓存其解",
    "斐波那契数列是重叠子问题的经典例子朴素递归会重复计算",
    "因此自底向上填表可将时间复杂度降为线性",
]

SEG_TEXTS = [
    "递归的核心结构是函数调用自身并逐步缩小问题规模",
    "求解阶乘时先写基准情形 n 等于零返回一再递归调用自身",
    "因此递归深度必须有限否则栈会溢出",
]


@pytest.fixture
def ass_file(tmp_path: Path) -> Path:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    f = corpus_dir / "ep01.ass"
    f.write_text(ASS_CONTENT, encoding="utf-8")
    return f


@pytest.fixture
def two_source_corpus(tmp_path: Path) -> Path:
    """两 Source 的 Corpus 目录（ep01 + ep02；文件名序确定）。"""

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "ep01.ass").write_text(ASS_CONTENT, encoding="utf-8")
    (corpus_dir / "ep02.ass").write_text(ASS_CONTENT_EP02, encoding="utf-8")
    return corpus_dir


def seg_id(n: int) -> str:
    return f"ep01#seg{n:04d}"


def make_units_with_time_range() -> tuple[KnowledgeUnit, ...]:
    """三个知识单元：claim / method / conclusion，全部带时间区间 locator。"""

    return (
        KnowledgeUnit(
            unit_id="u-001",
            unit_type="claim",
            statement="递归的核心结构是函数调用自身并逐步缩小问题规模",
            source_reference=SourceReference(
                segment_id=seg_id(1),
                quoted_text=SEG_TEXTS[0],
                locator=TimeRangeLocator(start_ms=1000, end_ms=6000),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-002",
            unit_type="method",
            statement="求阶乘：先写基准情形 n=0 返回 1，再递归调用自身",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=SEG_TEXTS[1],
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-003",
            unit_type="conclusion",
            statement="递归深度必须有限，否则栈会溢出",
            source_reference=SourceReference(
                segment_id=seg_id(3),
                quoted_text=SEG_TEXTS[2],
                locator=TimeRangeLocator(start_ms=14000, end_ms=18300),
            ),
        ),
    )


def make_unit_text_position() -> KnowledgeUnit:
    """带文本位置 locator 的单元：证明 locator 结构不锁死时间区间（R1.4）。"""

    return KnowledgeUnit(
        unit_id="u-textpos",
        unit_type="explanation",
        statement="基准情形的存在使递归能终止",
        source_reference=SourceReference(
            segment_id=seg_id(2),
            quoted_text=SEG_TEXTS[1],
            locator=TextPositionLocator(segment_id=seg_id(2), char_start=0, char_end=9),
        ),
    )


def seg2_id(n: int) -> str:
    return f"ep02#seg{n:04d}"


def make_ep02_units() -> tuple[KnowledgeUnit, ...]:
    """ep02 的三个知识单元：claim / explanation / conclusion，全部锚定
    ep02 自己的 Segment——与 ep01 的单元互不重叠。"""

    return (
        KnowledgeUnit(
            unit_id="u-101",
            unit_type="claim",
            statement="动态规划通过缓存重叠子问题的解避免重复计算",
            source_reference=SourceReference(
                segment_id=seg2_id(1),
                quoted_text=EP02_SEG_TEXTS[0],
                locator=TimeRangeLocator(start_ms=1000, end_ms=5500),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-102",
            unit_type="explanation",
            statement="斐波那契朴素递归慢在同一子问题被重复求解",
            source_reference=SourceReference(
                segment_id=seg2_id(2),
                quoted_text=EP02_SEG_TEXTS[1],
                locator=TimeRangeLocator(start_ms=6000, end_ms=11800),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-103",
            unit_type="conclusion",
            statement="自底向上填表把动态规划的时间复杂度降为线性",
            source_reference=SourceReference(
                segment_id=seg2_id(3),
                quoted_text=EP02_SEG_TEXTS[2],
                locator=TimeRangeLocator(start_ms=12400, end_ms=17000),
            ),
        ),
    )
