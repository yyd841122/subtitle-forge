"""ASS 字幕解析：.ass 文件 → Source（Segment 序列）。

V1 验收范围只有 ASS（R1.2）。解析保持最小可用：读取 [Events] 段的
Dialogue 行，剥离 ASS 内联样式标记（{\\...} override blocks 与绘制命令），
保留文本本体。其他格式的接入不被架构性排除——新格式实现同样的
"文件内容 → Source" 纯函数即可挂入（02 票裁定扩展形态）。
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Corpus, Segment, Source

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

    幂等、确定性：同一输入总是得到同一 Source。无 Dialogue 行的文件
    解析为空 Segment 的 Source（是否构成失败由运行侧裁定，不在解析层
    预设——R1.3 噪声容忍的边界之一）。
    """

    segments: list[Segment] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line.startswith("Dialogue:"):
            continue
        m = _DIALOGUE_RE.match(line)
        if m is None:
            continue  # 容错：无法解析的行跳过，不中断整 Source（R1.3 精神）
        layer, start, end, *_style_fields, raw_text = m.groups()
        text = _clean_ass_text(raw_text)
        if not text:
            continue  # 空文本事件（纯绘制命令等）不构成 Segment
        segments.append(
            Segment(
                segment_id=f"{source_id}#seg{len(segments) + 1:04d}",
                text=text,
                start_ms=_parse_ass_timestamp(start),
                end_ms=_parse_ass_timestamp(end),
            )
        )
    return Source(source_id=source_id, segments=tuple(segments))


def load_ass_file(path: Path) -> Source:
    """读取一个 .ass 文件为 Source。source_id 取文件名（不含扩展名）。"""

    return parse_ass_content(path.read_text(encoding="utf-8-sig"), path.stem)


def load_corpus(corpus_dir: Path) -> Corpus:
    """目录内全部 .ass 文件（按文件名排序）→ Corpus。

    Ticket 01 只有单 Source 形态；多 Source 批处理语义归 02 票，这里
    只提供最小的目录读取，不预设任何批处理策略。
    """

    files = sorted(corpus_dir.glob("*.ass"))
    return Corpus(sources=tuple(load_ass_file(f) for f in files))
