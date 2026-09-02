"""资产落盘：外部产物 → 按 Source 组织的可移植文件资产（初始形态，Open Impl 7）。

规范源形态（ADR-0006 裁定，15 票可修正迁移）：人可读 Markdown 为主、
结构内嵌 JSON 代码块。忠实层/审查层、基础层/衍生层的概念边界在目录
组织中成立（Ticket 01 完成项；R2.5、R2.6 的结构前提）：

    <asset_root>/
      sources/<source_id>/
        knowledge-units.md      # 忠实层：知识单元（含来源引用）
      review/                   # 审查层：系统判断（Review Note 归 09 票）
      derived/                  # 衍生层：跨 Source 结构（可整体重算）
      trusted-set.md            # 可信发布集（全 Corpus）
      gap-report.md             # 缺口报告
      run-summary.md            # 运行摘要

时间戳等运行元数据写入独立行（前缀 run-metadata），内容比对可排除。
"""

from __future__ import annotations

import json
from pathlib import Path

from .artifacts import GapReport, RunSummary, TrustedSet
from .model import KnowledgeUnit, Source


def _fence(obj) -> str:
    return "```json\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n```"


# ---------------------------------------------------------------------------
# 忠实层：按 Source 的知识单元资产
# ---------------------------------------------------------------------------

def write_source_asset(
    dir_root: Path,
    source: Source,
    units: list[KnowledgeUnit],
) -> Path:
    """写一个 Source 的忠实层资产（基础层，独立成立）。

    每单元记录：类型、陈述、来源引用（原文文本片段 + locator）。
    locator 含 kind 字段——时间区间只是 V1 实例，非必填语义（R1.4）。
    """

    out_dir = dir_root / "sources" / source.source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "knowledge-units.md"

    units_json = [
        {
            "unit_id": u.unit_id,
            "unit_type": u.unit_type,
            "statement": u.statement,
            "source_reference": None
            if u.source_reference is None
            else {
                "segment_id": u.source_reference.segment_id,
                "quoted_text": u.source_reference.quoted_text,
                "locator": {
                    "kind": u.source_reference.locator.kind,
                    **{
                        k: v
                        for k, v in u.source_reference.locator.__dict__.items()
                        if k != "kind"
                    },
                },
            },
        }
        for u in units
    ]
    lines = [
        f"# 知识单元 — {source.source_id}",
        "",
        "忠实层资产：忠实表达来源内容。系统判断不写入本文件（审查层在 review/）。",
        "",
        _fence({"source_id": source.source_id, "units": units_json}),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 全局产物
# ---------------------------------------------------------------------------

def write_trusted_set(dir_root: Path, trusted: TrustedSet) -> Path:
    path = dir_root / "trusted-set.md"
    entries = [
        {
            "source_id": e.source_id,
            "unit_id": e.unit_id,
            "unit_type": e.unit_type,
            "statement": e.statement,
            "source_reference": {
                "segment_id": e.segment_id,
                "quoted_text": e.quoted_text,
                "locator": e.locator,
            },
        }
        for e in trusted.entries
    ]
    lines = [
        "# 可信发布集（Trusted Set）",
        "",
        "由审计通过的知识单元组成。成员资格只由知识单元的审计结果决定（ADR-0003）。",
        "",
        _fence({"entries": entries}),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_gap_report(dir_root: Path, report: GapReport) -> Path:
    path = dir_root / "gap-report.md"
    entries = [
        {
            "category": e.category,
            "source_id": e.source_id,
            "subject": e.subject,
            "reason": e.reason,
            "outcome": e.outcome,
        }
        for e in report.entries
    ]
    lines = [
        "# 缺口报告（Gap Report）",
        "",
        "一等资产：显性记录异常与缺口（四类缺口类别：执行失败 / 审计拒绝 / "
        "覆盖存疑 / 警告）。不承担全量正常对账（对账见运行摘要）。",
        "",
        _fence(
            {
                "categories": [
                    "execution_failure",
                    "audit_rejection",
                    "coverage_concern",
                    "warning",
                ],
                "entries": entries,
            }
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_run_summary(dir_root: Path, summary: RunSummary) -> Path:
    path = dir_root / "run-summary.md"
    sources = [
        {
            "source_id": r.source_id,
            "status": r.status,
            "reason": r.reason,
            "units": [
                {"unit_id": u.unit_id, "status": u.status, "reason": u.reason}
                for u in r.units
            ],
        }
        for r in summary.sources
    ]
    lines = [
        "# 运行摘要（Run Summary）",
        "",
        "一次运行的全量去向对账：每个 Source 与每个知识单元均有实体状态，无静默消失。",
        "",
        _fence({"sources": sources, "role_call_counts": summary.role_call_counts}),
        "",
        f"run-metadata: wall_time_ms={summary.wall_time_ms}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_all(
    dir_root: Path,
    source: Source,
    units: list[KnowledgeUnit],
    trusted: TrustedSet,
    gaps: GapReport,
    summary: RunSummary,
    with_global: bool = True,
) -> list[Path]:
    """落盘一个 Source 的资产；``with_global`` 时同时写全 Corpus 的全局产物
    （可信发布集/缺口报告/运行摘要——含空但结构完整的审查层/衍生层
    占位目录）。单 Source 形态下每 Source 都写全局产物亦无害（幂等）。"""

    written = [write_source_asset(dir_root, source, units)]
    (dir_root / "review").mkdir(parents=True, exist_ok=True)
    (dir_root / "derived").mkdir(parents=True, exist_ok=True)
    (dir_root / "review" / ".gitkeep").write_text("", encoding="utf-8")
    (dir_root / "derived" / ".gitkeep").write_text("", encoding="utf-8")
    if with_global:
        written.append(write_trusted_set(dir_root, trusted))
        written.append(write_gap_report(dir_root, gaps))
        written.append(write_run_summary(dir_root, summary))
    return written
