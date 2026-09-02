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
