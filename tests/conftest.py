"""共享 fixture 与测试辅助：受控 ASS Source、按认知角色独立注入的确定性
替身、外部产物的解析辅助。

测试输入的一部分（Testing Decisions）：替身按认知角色分别注入、分别
设定行为。断言只针对外部产物——``parse_json_block`` 模拟"机器是一级
消费者"，从落盘 Markdown 的 json 代码块解析结构，不 import 内部结构。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from subtitle_forge.model import (
    KnowledgeUnit,
    SourceReference,
    TextPositionLocator,
    TimeRangeLocator,
)

# ---------------------------------------------------------------------------
# 外部产物解析辅助（机器是一级消费者：不 import 内部结构）
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def parse_json_block(path: Path) -> dict:
    """从落盘产物的第一个 json 代码块解析结构；无代码块即失败。"""

    text = path.read_text(encoding="utf-8")
    blocks = _JSON_BLOCK_RE.findall(text)
    assert blocks, f"{path} 应含机器可解析的 json 代码块"
    return json.loads(blocks[0])


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

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


def make_units_a2_overreach() -> tuple[KnowledgeUnit, ...]:
    """A2（推理审计）场景的三个单元：u-002 带真实存在于原文的引用
    （锚定 seg2，只讲阶乘的基准情形），但陈述明显越界——推广为一切
    递归函数的基准情形。推理审查替身据此对 u-002 预设 reject（票 03
    的受控输入：引用真实存在，断言超出引用支持范围）。"""

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
            unit_type="claim",
            statement="一切递归函数的基准情形都是 n 等于零时返回一",
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


# ---------------------------------------------------------------------------
# Ticket 04 受控输入：忠实性程序比对（A1 假引用 + 最小规范化容差对照）
# ---------------------------------------------------------------------------

# 编造的引用文本：读起来像课程内容，但不存在于 ep01 任何 Segment 的
# 原文（假引用的受控种子，A1）。
FAKE_QUOTE_TEXT = "任何递归函数的基准情形都在 n 等于一时返回一"


def make_units_a1_fake_quote() -> tuple[KnowledgeUnit, ...]:
    """A1（忠实性程序比对）场景的三个单元：u-002 的 quoted_text 是编造
    的——锚定 seg2 但其文本不存在于原文；u-001/u-003 带真实引用。推理
    审计替身对全部单元判 pass（默认），假引用只可能被程序门拦截
    （AC1 的前提：推理审计通过 + 程序比对不成立）。"""

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
            unit_type="claim",
            statement="基准情形在 n 等于一时返回一",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=FAKE_QUOTE_TEXT,
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


# 受控 ASS（换行排版）：seg2 文本含字面 \N 换行——解析后 Segment.text
# 保留换行字符（ass.py 裁定：规范化方式由比对端决定），供忠实性比对
# 最小规范化容差的受控验证（04 票内裁定的初始算法）。
ASS_CONTENT_NEWLINE = """[Script Info]
Title: 受控课程 换行排版
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:06.00,Default,,0,0,0,,递归的核心结构是函数调用自身并逐步缩小问题规模
Dialogue: 0,0:00:07.50,0:00:13.20,Default,,0,0,0,,求解阶乘分两步\\N先写基准情形再递归调用自身
Dialogue: 0,0:00:14.00,0:00:18.30,Default,,0,0,0,,因此递归深度必须有限否则栈会溢出
"""

# 解析后 seg2 的原文形态：\\N 成为换行字符（文本本体不变）。
# 下方变体单元的引用文本由此显式派生，引用与受控输入的对应关系可查。
NEWLINE_SEG2_TEXT = "求解阶乘分两步\n先写基准情形再递归调用自身"


@pytest.fixture
def newline_ass_file(tmp_path: Path) -> Path:
    corpus_dir = tmp_path / "corpus-newline"
    corpus_dir.mkdir()
    f = corpus_dir / "ep01.ass"
    f.write_text(ASS_CONTENT_NEWLINE, encoding="utf-8")
    return f


def make_units_newline_variants() -> tuple[KnowledgeUnit, ...]:
    """最小规范化容差的对照单元（锚定换行 seg2）：u-nl-space 的引用
    文本仅以空格代替原文换行（排版差异，规范化后比对成立）；
    u-nl-alter 在同样排版之上还改动一个非空白字符（两→三，任何规范化
    下都不成立）——初始算法"只容忍排版、不容忍内容改动"的受控对照。
    引用文本由 NEWLINE_SEG2_TEXT 显式派生（换行→空格 / 再改一字）。"""

    space_quote = NEWLINE_SEG2_TEXT.replace("\n", " ")
    altered_quote = space_quote.replace("两", "三")
    return (
        KnowledgeUnit(
            unit_id="u-nl-space",
            unit_type="claim",
            statement="求解阶乘分两步：先写基准情形再递归调用自身",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=space_quote,
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-nl-alter",
            unit_type="claim",
            statement="求解阶乘分三步：先写基准情形再递归调用自身",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=altered_quote,
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
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
