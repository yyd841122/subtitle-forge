"""共享 fixture 与测试辅助：受控 ASS Source、按认知角色独立注入的确定性
替身、外部产物的解析辅助。

测试输入的一部分（Testing Decisions）：替身按认知角色分别注入、分别
设定行为。断言只针对外部产物——``parse_json_block`` 模拟"机器是一级
消费者"，从落盘 Markdown 的 json 代码块解析结构，不 import 内部结构。
"""

from __future__ import annotations

import json
import re
import sys
import types
from pathlib import Path

import pytest

from subtitle_forge.model import (
    KnowledgeUnit,
    SourceReference,
    TextPositionLocator,
    TimeRangeLocator,
)
from subtitle_forge.roles import CognitiveRoles

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


def run_cli_with_roles(
    corpus_path: Path,
    asset_dir: Path,
    roles: CognitiveRoles,
    module_name: str,
) -> int:
    """注册替身模块并执行 CLI（含落盘），返回退出码——各票测试共用的
    端到端执行通道（替身注入是测试输入的一部分，Testing Decisions）。

    ``corpus_path`` 可为单个 .ass 文件或 Corpus 目录。各票测试经本地
    包装（默认模块名 + 票内断言）调用，不在测试文件间重复注册管线。
    """

    mod = types.ModuleType(module_name)
    mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
    sys.modules[module_name] = mod
    from subtitle_forge.cli import main

    corpus_dir = corpus_path.parent if corpus_path.is_file() else corpus_path
    return main(["run", str(corpus_dir), str(asset_dir), "--stub-module", module_name])

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


# 受控课程 03 的 ASS 内容（与 ep01/ep02 主题互异：二分查找）。三 Source
# 批处理「失败隔离」的受控输入（票 07：中间 Source 抛错，前后 Source
# 照常完成的对照形态）。
ASS_CONTENT_EP03 = """[Script Info]
Title: 受控课程 03
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,二分查找要求数据有序并在每次比较后排除一半候选
Dialogue: 0,0:00:06.00,0:00:10.50,Default,,0,0,0,,对数复杂度使二分查找在大规模有序数据上远快于线性扫描
Dialogue: 0,0:00:11.00,0:00:15.00,Default,,0,0,0,,因此有序数据上的查找应优先考虑二分策略
"""

EP03_SEG_TEXTS = [
    "二分查找要求数据有序并在每次比较后排除一半候选",
    "对数复杂度使二分查找在大规模有序数据上远快于线性扫描",
    "因此有序数据上的查找应优先考虑二分策略",
]


@pytest.fixture
def three_source_corpus(tmp_path: Path) -> Path:
    """三 Source 的 Corpus 目录（ep01 + ep02 + ep03；文件名序确定）。"""

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "ep01.ass").write_text(ASS_CONTENT, encoding="utf-8")
    (corpus_dir / "ep02.ass").write_text(ASS_CONTENT_EP02, encoding="utf-8")
    (corpus_dir / "ep03.ass").write_text(ASS_CONTENT_EP03, encoding="utf-8")
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


# ---------------------------------------------------------------------------
# Ticket 05 受控输入：待复核（inconclusive）语义（A14 无法可靠判定）
# ---------------------------------------------------------------------------


def make_units_a14_inconclusive() -> tuple[KnowledgeUnit, ...]:
    """A14（待复核语义）场景的三个单元：u-002 的引用真实存在于原文
    （锚定 seg2），但陈述在两个 Segment（基准情形的写法 / 递归深度有限）
    之间架起因果关系——原文分别提到两者、从未直接表述这层联系，它
    既非逐字支持的转述（可通过）、也非明确越界的推广（可拒绝）：
    是隐含结论还是超出范围，取决于解释性判断，推理上无法可靠判定。
    推理审计替身据此对 u-002 预设 inconclusive + 理由（受控触发 05 票
    语义：R4.4 的"无法可靠判定"，非低质量兜底）。u-001/u-003 陈述与
    引用直接对应，照常通过——"其余单元不受影响"的对照组。"""

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
            statement="写对基准情形是递归深度保持有限的前提",
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
# Ticket 06 受控输入：无 Source Reference 单元的下落（A17 / R2.4）
# ---------------------------------------------------------------------------


def make_units_a17_no_reference() -> tuple[KnowledgeUnit, ...]:
    """A17（引用不变量）场景的三个单元：u-002 无 Source Reference——
    陈述本身是正常的知识表达（提炼替身的完整产物，不是执行失败），
    但缺少追溯锚点（引用文本 + 定位），不构成可信发布集的准入凭据；
    u-001/u-003 带真实引用照常通过——"其余正常"的对照组。推理审计
    替身对全部单元默认 pass（受控前提：无引用单元只可能被无引用门
    处置，06 票场景）。"""

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
            statement="求阶乘：先写基准情形，再递归调用自身",
            source_reference=None,
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


def make_ep03_units() -> tuple[KnowledgeUnit, ...]:
    """ep03 的三个知识单元：claim / explanation / conclusion，全部锚定
    ep03 自己的 Segment——三 Source 批处理的第三组互不重叠单元（票 07）。"""

    return (
        KnowledgeUnit(
            unit_id="u-201",
            unit_type="claim",
            statement="二分查找要求数据有序，每次比较排除一半候选",
            source_reference=SourceReference(
                segment_id=seg3_id(1),
                quoted_text=EP03_SEG_TEXTS[0],
                locator=TimeRangeLocator(start_ms=1000, end_ms=5000),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-202",
            unit_type="explanation",
            statement="对数复杂度使二分查找在大规模有序数据上远快于线性扫描",
            source_reference=SourceReference(
                segment_id=seg3_id(2),
                quoted_text=EP03_SEG_TEXTS[1],
                locator=TimeRangeLocator(start_ms=6000, end_ms=10500),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-203",
            unit_type="conclusion",
            statement="有序数据上的查找应优先考虑二分策略",
            source_reference=SourceReference(
                segment_id=seg3_id(3),
                quoted_text=EP03_SEG_TEXTS[2],
                locator=TimeRangeLocator(start_ms=11000, end_ms=15000),
            ),
        ),
    )


def seg3_id(n: int) -> str:
    return f"ep03#seg{n:04d}"


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


# ---------------------------------------------------------------------------
# Ticket 08 受控输入：解析级畸形（warning 显性化）与内容级噪声（A13 确定性）
# ---------------------------------------------------------------------------

# 受控 ASS（解析噪声）：两类票面钉死的畸形（L12 字段不足 → 正则不匹配；
# L13 清洗后空文本）+ 一类票内裁定的畸形（L15 无效时间戳 → warning 化
# 并跳过）。知识行 L11/L14 照常解析为 Segment——"跳过不中断、其余
# 照常"的对照形态。行号由本 fixture 钉死（L11/12/13/14/15），供
# warning 条目的行号断言。
ASS_CONTENT_MALFORMED = """[Script Info]
Title: 受控课程 解析噪声
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:06.00,Default,,0,0,0,,递归的核心结构是函数调用自身并逐步缩小问题规模
Dialogue: 0,0:00:01.00,Default
Dialogue: 0,0:00:07.50,0:00:13.20,Default,,0,0,0,,{\\pos(1,2)}{\\fad(100,100)}
Dialogue: 0,0:00:07.50,0:00:13.20,Default,,0,0,0,,求解阶乘时先写基准情形 n 等于零返回一{\\an8}再递归调用自身
Dialogue: 0,0:0X:14.00,0:00:18.30,Default,,0,0,0,,因此递归深度必须有限否则栈会溢出
"""

# 畸形 fixture 的钉死行号（与上方内容一一对应；改动内容须同步此处）。
MALFORMED_LINENO_INSUFFICIENT_FIELDS = 12
MALFORMED_LINENO_EMPTY_TEXT = 13
MALFORMED_LINENO_INVALID_TIMESTAMP = 15


@pytest.fixture
def malformed_ass_file(tmp_path: Path) -> Path:
    """含三类解析畸形的 .ass 文件（独立 corpus 目录、单 Source ep01）。
    知识 Segment 只剩两个（L11/L14）——L15 的知识内容随时间戳损坏被
    跳过，其损失由 warning 条目的行内容显性化（A11）。"""

    corpus_dir = tmp_path / "corpus-malformed"
    corpus_dir.mkdir()
    f = corpus_dir / "ep01.ass"
    f.write_text(ASS_CONTENT_MALFORMED, encoding="utf-8")
    return f


def make_malformed_units() -> tuple[KnowledgeUnit, ...]:
    """畸形 fixture 的两个知识单元：只锚定照常解析的知识 Segment
    （seg0001 ← L11、seg0002 ← L14）——"知识单元照常"的受控脚本。"""

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
    )


# 受控 ASS（内容噪声，A13 确定性半边）：七条 Dialogue 全部结构正常
# （无解析畸形 ⇒ 无 warning），其中四条是内容级噪声——L11 口头填充
# 开场、L13 重复、L15 轻微转写错误（接乘/阶乘 自我纠正）、L17 寒暄
# 收尾；三条知识行（L12/L14/L16）与 ep01 的知识文本一致。知识单元
# 只锚定知识 Segment（替身脚本化）——噪声进不了知识单元的机制本身。
ASS_CONTENT_NOISY = """[Script Info]
Title: 受控课程 内容噪声
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.50,0:00:02.00,Default,,0,0,0,,呃 那个 今天我们开始讲递归
Dialogue: 0,0:00:02.10,0:00:07.00,Default,,0,0,0,,递归的核心结构是函数调用自身并逐步缩小问题规模
Dialogue: 0,0:00:07.10,0:00:09.00,Default,,0,0,0,,嗯 函数调用自身 函数调用自身 就是缩小问题规模 嗯
Dialogue: 0,0:00:09.10,0:00:14.00,Default,,0,0,0,,求解阶乘时先写基准情形 n 等于零返回一再递归调用自身
Dialogue: 0,0:00:14.10,0:00:16.00,Default,,0,0,0,,呃 求解接乘 求解阶乘 对吧 先写基准情形
Dialogue: 0,0:00:16.10,0:00:20.00,Default,,0,0,0,,因此递归深度必须有限否则栈会溢出
Dialogue: 0,0:00:20.10,0:00:22.00,Default,,0,0,0,,好 那我们今天就讲到这里 谢谢大家
"""

# 噪声片段清单（受控钉死）：口头填充（呃/那个/嗯/对吧）、转写错字
# （接乘）、寒暄（谢谢大家）、重复形态（连续两遍的"函数调用自身"）。
# 断言依据：这些片段均不出现在任何知识单元的 statement / quoted_text
# （知识文本 SEG_TEXTS 与干净 statement 均不含它们——受控可验证）。
NOISE_FRAGMENTS = (
    "呃",
    "那个",
    "嗯",
    "对吧",
    "接乘",
    "谢谢大家",
    "函数调用自身 函数调用自身",
)

# 纯噪声 Segment 的原文（L11 解析产物）：边界测试的逐字引用来源——
# 系统准入门不得对其做内容过滤（08 票明确不含，触界行为）。
NOISY_SEG1_TEXT = "呃 那个 今天我们开始讲递归"

# 噪声 fixture 中知识 Segment 的位置（ Dialogue 行序 = Segment 序）：
# seg0002 ← L12、seg0004 ← L14、seg0006 ← L16（噪声行各自占位但不获锚定）。


def noisy_seg_id(n: int) -> str:
    return f"noisy#seg{n:04d}"


@pytest.fixture
def noisy_ass_file(tmp_path: Path) -> Path:
    """含内容级噪声的 .ass 文件（独立 corpus 目录、单 Source noisy）。"""

    corpus_dir = tmp_path / "corpus-noisy"
    corpus_dir.mkdir()
    f = corpus_dir / "noisy.ass"
    f.write_text(ASS_CONTENT_NOISY, encoding="utf-8")
    return f


def make_noisy_units() -> tuple[KnowledgeUnit, ...]:
    """噪声 fixture 的三个知识单元：claim / method / conclusion，只锚定
    知识 Segment（seg0002/seg0004/seg0006），statement 与 quoted_text
    均为干净知识文本——"噪声不出现在知识单元"的替身脚本化实现
    （内容判断属提炼角色；真实角色的判断质量由 29 票 eval 覆盖）。"""

    return (
        KnowledgeUnit(
            unit_id="u-n001",
            unit_type="claim",
            statement="递归的核心结构是函数调用自身并逐步缩小问题规模",
            source_reference=SourceReference(
                segment_id=noisy_seg_id(2),
                quoted_text=SEG_TEXTS[0],
                locator=TimeRangeLocator(start_ms=2100, end_ms=7000),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-n002",
            unit_type="method",
            statement="求阶乘：先写基准情形 n=0 返回 1，再递归调用自身",
            source_reference=SourceReference(
                segment_id=noisy_seg_id(4),
                quoted_text=SEG_TEXTS[1],
                locator=TimeRangeLocator(start_ms=9100, end_ms=14000),
            ),
        ),
        KnowledgeUnit(
            unit_id="u-n003",
            unit_type="conclusion",
            statement="递归深度必须有限，否则栈会溢出",
            source_reference=SourceReference(
                segment_id=noisy_seg_id(6),
                quoted_text=SEG_TEXTS[2],
                locator=TimeRangeLocator(start_ms=16100, end_ms=20000),
            ),
        ),
    )
