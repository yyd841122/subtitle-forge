"""ASS 字幕解析：.ass 文件 → Source（Segment 序列 + 解析警告）。

V1 验收范围只有 ASS（R1.2）。解析保持最小可用：读取 [Events] 段的
Dialogue 行，剥离 ASS 内联样式标记（{\\...} override blocks 与绘制命令），
保留文本本体。其他格式的接入不被架构性排除（R1.2：解析层可扩展，
具体格式不在 V1 验收范围）——新格式实现同样的"文件内容 → Source"
纯函数即可挂入。

解析级噪声容忍（08 票，R1.3 显性化）：被容忍跳过的输入行不再静默——
每处跳过记一条 ParseWarning（行号 + 人可读原因，含行内容），随
``Source.parse_warnings`` 传给运行侧，落缺口报告 warning 条目（A11）。
跳过三类（前两类为票面钉死，第三类为票内裁定）：
(a) 字段数不足、正则不匹配的 Dialogue 行；(b) 清洗后空文本的事件
（纯样式/绘制标记）；(c) 时间戳无法解析的行（裁定：warning 化并跳过，
非全局错误——理由见 parse 处注释）。跳过不使 Source 失败（R1.3），
其观察不改变 Source 的实体状态。
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Corpus, ParseWarning, Segment, Source

# ASS Dialogue 行：Dialogue: 0,0:00:01.00,0:00:03.50,Style,,0,0,0,,文本
_DIALOGUE_RE = re.compile(r"^Dialogue:\s*([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),(.*)$")
# ASS 内联 override block：{\an8}、{\pos(...)}、{\fad(...)} 等。
_OVERRIDE_BLOCK_RE = re.compile(r"\{[^}]*\}")
# 换行符在 ASS 文本里是字面 \N / \n，语义为换行；引用比对前统一成空格
# 会破坏逐字性，这里保留为换行字符本身，由比对端决定规范化方式。
_NEWLINE_RE = re.compile(r"\\[Nn]")


def _parse_ass_timestamp(ts: str) -> int:
    """'0:01:02.34' → 毫秒（ASS 时间戳格式 H:MM:SS.cc，厘秒两位）。"""

    ts = ts.strip()
    h, m, rest = ts.split(":")
    s, cs = rest.split(".")
    cs = (cs + "00")[:2]  # 容错：不足两位补零，超出截断
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(cs) * 10


def _clean_ass_text(raw: str) -> str:
    """剥离内联样式与绘制标记，保留文本本体与换行语义。"""

    text = _OVERRIDE_BLOCK_RE.sub("", raw)
    text = _NEWLINE_RE.sub("\n", text)
    return text.strip()


def parse_ass_content(content: str, source_id: str) -> Source:
    """ASS 文件文本 → Source。纯函数，不做任何 I/O。

    幂等、确定性：同一输入总是得到同一 Source（Segment 与
    parse_warnings 均确定）。无 Dialogue 行的文件解析为空 Segment 的
    Source（是否构成失败由运行侧裁定，不在解析层预设——R1.3 噪声容忍
    的边界之一）；无跳过的解析不产生任何警告（清洁输入 warning 为空）。
    """

    segments: list[Segment] = []
    warnings: list[ParseWarning] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line.startswith("Dialogue:"):
            # 非 Dialogue 行是格式的正常结构（头信息、样式、注释等），
            # 不是噪声——静默忽略，不记警告（AC3：清洁运行 warning 为空）。
            continue
        m = _DIALOGUE_RE.match(line)
        if m is None:
            # 容错：无法解析的行跳过，不中断整 Source（R1.3）——
            # 跳过事实显性化（08 票）：warning 条目承载行号与行内容。
            warnings.append(
                ParseWarning(
                    lineno=lineno,
                    reason=f"Dialogue 行无法按事件结构解析（逗号分隔字段不足）：{line}",
                )
            )
            continue
        layer, start, end, *_style_fields, raw_text = m.groups()
        text = _clean_ass_text(raw_text)
        if not text:
            # 空文本事件（纯绘制命令等）不构成 Segment——跳过事实
            # 显性化（08 票）。
            warnings.append(
                ParseWarning(
                    lineno=lineno,
                    reason=f"清洗后文本为空（纯样式/绘制标记），不构成知识性事件：{line}",
                )
            )
            continue
        try:
            start_ms = _parse_ass_timestamp(start)
            end_ms = _parse_ass_timestamp(end)
        except ValueError:
            # 票内裁定（08 票）：无效时间戳 warning 化并跳过该行，非全局
            # 错误。理由：(a) 单行时间戳损坏是典型的转写/制作噪声，让它
            # 中止整批违背 R1.3（噪声不得导致整 Source 失败）；(b) 保留
            # 该行为无时间戳 Segment 则超出 V1 验收——时间区间是 V1 ASS
            # 输入的验收形态，无时间轴 Segment 无法携带 V1 可验收的
            # Source Reference locator（R1.4/Q26：文本位置定位 V1 不
            # 验收）；(c) 行内容进 warning 原因，知识损失显性可审计
            # （A11，不静默消失）。只捕获 ValueError（时间戳解析的已知
            # 失败形态——缺分隔符 / 非数字），其他异常维持 fail loud。
            warnings.append(
                ParseWarning(
                    lineno=lineno,
                    reason=f"时间戳无法解析（开始 {start!r} / 结束 {end!r}），该行跳过：{line}",
                )
            )
            continue
        segments.append(
            Segment(
                segment_id=f"{source_id}#seg{len(segments) + 1:04d}",
                text=text,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )
    return Source(
        source_id=source_id, segments=tuple(segments), parse_warnings=tuple(warnings)
    )


def load_ass_file(path: Path) -> Source:
    """读取一个 .ass 文件为 Source。source_id 取文件名（不含扩展名）。"""

    return parse_ass_content(path.read_text(encoding="utf-8-sig"), path.stem)


def load_corpus(corpus_dir: Path) -> Corpus:
    """目录内全部 .ass 文件（按文件名排序）→ Corpus。

    批处理顺序语义（Ticket 02 票内裁定）：文件名序、确定性。R1.1：
    Corpus 是批处理单位——这里只做读取与排序，不预设跳过/运行范围
    控制等运行策略。
    """

    files = sorted(corpus_dir.glob("*.ass"))
    return Corpus(sources=tuple(load_ass_file(f) for f in files))
