"""ASS 解析器单元测试。

非验收测试（验收一律走端到端接缝，Testing Decisions）：解析是纯函数，
按输入/输出直接验证。端到端对解析的消费由 test_walking_skeleton 覆盖；
解析级噪声的端到端验收（warning 条目落缺口报告）由 test_noise_tolerance
覆盖（08 票）。
"""

from __future__ import annotations

from subtitle_forge.ass import parse_ass_content

ASS_SAMPLE = """[Script Info]
Title: 样例
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:06.00,Default,,0,0,0,,第一句知识内容
Dialogue: 0,0:00:07.50,0:00:13.20,Default,,0,0,0,,第二句{\\an8}含样式标记
Comment: 0,0:00:07.50,0:00:13.20,Default,,0,0,0,,注释行不是事件
Dialogue: 0,0:00:14.00,0:00:18.30,Default,,0,0,0,,{\\pos(1,2)}定位标记后仍有正文
Dialogue: 0,0:00:19.00,0:00:19.50,Default,,0,0,0,,{\\pos(1,2)}{\\fad(100,100)}
Dialogue: 0,0:00:20.00,0:00:22.00,Default,,0,0,0,,带换行\\N的第二段
"""


def test_dialogues_parsed_with_text_and_time():
    source = parse_ass_content(ASS_SAMPLE, "ep01")
    assert source.source_id == "ep01"
    texts = [s.text for s in source.segments]
    # 注释行、剥净后无正文的行不构成 Segment；override 标记剥离；
    # \N 保留换行语义
    assert texts == ["第一句知识内容", "第二句含样式标记", "定位标记后仍有正文", "带换行\n的第二段"]
    assert [s.segment_id for s in source.segments] == [
        "ep01#seg0001",
        "ep01#seg0002",
        "ep01#seg0003",
        "ep01#seg0004",
    ]


def test_skipped_lines_recorded_as_parse_warnings():
    """08 票（解析级）：被容忍跳过的行不静默——每处跳过记一条
    ParseWarning（行号 + 原因含行内容）。ASS_SAMPLE 的空文本行（纯
    绘制标记）是唯一的跳过；注释行是正常格式结构，不记警告。"""

    source = parse_ass_content(ASS_SAMPLE, "ep01")
    assert [(w.lineno, w.reason) for w in source.parse_warnings] == [
        (
            15,
            "清洗后文本为空（纯样式/绘制标记），不构成知识性事件："
            "Dialogue: 0,0:00:19.00,0:00:19.50,Default,,0,0,0,,{\\pos(1,2)}{\\fad(100,100)}",
        )
    ]


def test_clean_parse_has_no_warnings():
    """清洁输入（无跳过）不携带任何解析警告（AC3 的解析层形态）。"""

    source = parse_ass_content(
        "[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,正文\n", "ep01"
    )
    assert source.parse_warnings == ()
    assert len(source.segments) == 1


def test_timestamps_parsed_to_milliseconds():
    source = parse_ass_content(ASS_SAMPLE, "ep01")
    first = source.segments[0]
    assert (first.start_ms, first.end_ms) == (1000, 6000)
    assert (source.segments[1].start_ms, source.segments[1].end_ms) == (7500, 13200)


def test_empty_content_yields_empty_source():
    source = parse_ass_content("[Script Info]\n", "empty")
    assert source.segments == ()
    assert source.parse_warnings == ()  # 格式结构不是噪声，无警告


def test_malformed_and_invalid_timestamp_lines_skipped_with_warnings():
    """08 票三类跳过的解析层钉死：字段不足（正则不匹配）、无效时间戳
    （开始与结束两个位置；票内裁定：warning 化并跳过，非全局错误）
    ——行号按输入行序，知识行照常成为 Segment（Segment 编号按留存序）。"""

    content = (
        "[Events]\n"
        "Dialogue: 0,0:00:01.00,0:00:06.00,Default,,0,0,0,,知识正文\n"
        "Dialogue: 0,0:00:01.00,Default\n"
        "Dialogue: 0,0:0X:14.00,0:00:18.30,Default,,0,0,0,,开始时间戳损坏的知识正文\n"
        "Dialogue: 0,0:00:07.50,0:0Y:08.50,Default,,0,0,0,,结束时间戳损坏的知识正文\n"
        "Dialogue: 0,0:00:09.10,0:00:10.00,Default,,0,0,0,,逗号后字段仍属正文,含第二逗号\n"
    )
    source = parse_ass_content(content, "ep01")
    assert [s.text for s in source.segments] == ["知识正文", "逗号后字段仍属正文,含第二逗号"]
    linenos = [w.lineno for w in source.parse_warnings]
    reasons = [w.reason for w in source.parse_warnings]
    assert linenos == [3, 4, 5]
    assert "字段" in reasons[0] and "Dialogue: 0,0:00:01.00,Default" in reasons[0]
    assert "时间戳" in reasons[1] and "开始时间戳损坏的知识正文" in reasons[1]
    assert "时间戳" in reasons[2] and "结束时间戳损坏的知识正文" in reasons[2]


def test_parsing_is_deterministic():
    assert parse_ass_content(ASS_SAMPLE, "ep01") == parse_ass_content(ASS_SAMPLE, "ep01")
