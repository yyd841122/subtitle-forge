"""ASS 解析器单元测试。

非验收测试（验收一律走端到端接缝，Testing Decisions）：解析是纯函数，
按输入/输出直接验证。端到端对解析的消费由 test_walking_skeleton 覆盖。
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


def test_timestamps_parsed_to_milliseconds():
    source = parse_ass_content(ASS_SAMPLE, "ep01")
    first = source.segments[0]
    assert (first.start_ms, first.end_ms) == (1000, 6000)
    assert (source.segments[1].start_ms, source.segments[1].end_ms) == (7500, 13200)


def test_empty_content_yields_empty_source():
    source = parse_ass_content("[Script Info]\n", "empty")
    assert source.segments == ()


def test_parsing_is_deterministic():
    assert parse_ass_content(ASS_SAMPLE, "ep01") == parse_ass_content(ASS_SAMPLE, "ep01")
