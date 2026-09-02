"""资产落盘：外部产物 → 按 Source 组织的可移植文件资产（初始形态，Open Impl 7）。

规范源形态（ADR-0006 裁定；终裁与迁移属 25 票）：人可读 Markdown 为主、
结构内嵌 JSON 代码块。忠实层/审查层、基础层/衍生层的概念边界在目录
组织中成立（Ticket 01 完成项；R2.5、R2.6 的结构前提）：

    <asset_root>/
      sources/<source_id>/
        knowledge-units.md      # 忠实层：知识单元（含来源引用）
      review/                   # 审查层：系统判断（Review Note 由审查
                                # 环节产出，R3.6；18 票落地）
      derived/                  # 衍生层：跨 Source 结构（可整体重算）
      trusted-set.md            # 可信发布集（全 Corpus）
      gap-report.md             # 缺口报告
      run-summary.md            # 运行摘要

时间戳等运行元数据写入独立行（前缀 run-metadata），内容比对可排除。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .artifacts import (
    SOURCE_STATUS_FAILED,
    SOURCE_STATUS_NEEDS_REVIEW,
    SOURCE_STATUS_SUCCESS,
    UNIT_STATUS_FAILED,
    UNIT_STATUS_NEEDS_REVIEW,
    UNIT_STATUS_PASSED,
    UNIT_STATUS_REJECTED,
    GapReport,
    RunSummary,
    TrustedSet,
)
from .model import KnowledgeUnit, Source


def _fence(obj) -> str:
    return "```json\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n```"


# ---------------------------------------------------------------------------
# 忠实层：按 Source 的知识单元资产
# ---------------------------------------------------------------------------

def write_source_asset(
    dir_root: Path,
    source: Source,
    units: Sequence[KnowledgeUnit],
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
            "coverage_audit": None
            if r.coverage is None
            else {"covered": r.coverage.covered, "reason": r.coverage.reason},
        }
        for r in summary.sources
    ]
    lines = [
        "# 运行摘要（Run Summary）",
        "",
        "一次运行的全量去向对账：每个 Source 与每个知识单元均有实体状态，无静默消失。",
        "",
        _fence(
            {
                # 状态枚举自描述（外部产物的可观察 schema，仿缺口报告的
                # categories 先例）：Source 级与 Knowledge Unit 级取值域。
                "source_status_values": [
                    SOURCE_STATUS_SUCCESS,
                    SOURCE_STATUS_FAILED,
                    SOURCE_STATUS_NEEDS_REVIEW,
                ],
                "unit_status_values": [
                    UNIT_STATUS_PASSED,
                    UNIT_STATUS_REJECTED,
                    UNIT_STATUS_NEEDS_REVIEW,
                    UNIT_STATUS_FAILED,
                ],
                # 资产组织自描述：忠实层（每 Source 独立成立）、审查层、
                # 衍生层的位置声明。层的概念边界由此可观察，而具体路径
                # 是声明的取值不是测试的假设——布局变更只改声明。
                "asset_organization": _asset_organization(dir_root),
                "sources": sources,
            }
        ),
        "",
        f"run-metadata: wall_time_ms={summary.wall_time_ms}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _asset_organization(dir_root: Path) -> dict:
    """从已写盘的目录结构生成资产组织清单（相对路径声明）。

    忠实层 = 各 Source 的知识资产；审查层 = 系统判断（Review Note，
    R3.6）；衍生层 = 跨 Source 可重算结构（R2.7 最小形态）。
    """

    faithful = sorted(
        str(p.relative_to(dir_root))
        for p in (dir_root / "sources").glob("*/knowledge-units.md")
    )
    return {
        "faithful_layer": {"per_source": faithful},
        "review_layer": {"path": "review", "holds": "系统判断（Review Note）"},
        "derived_layer": {"path": "derived", "holds": "跨 Source 衍生结构（可整体重算）"},
    }


def write_all(
    dir_root: Path,
    sources: Sequence[Source],
    source_units: Mapping[str, Sequence[KnowledgeUnit]],
    trusted: TrustedSet,
    gaps: GapReport,
    summary: RunSummary,
) -> list[Path]:
    """落盘全部产物：每个 Source 的忠实层资产（R6.4：资产与 Source 明确
    对应）+ 全局产物（可信发布集/缺口报告/运行摘要），含空但结构完整的
    审查层/衍生层占位目录。

    ``source_units`` 与 ``sources`` 一一对应（管线保证每个处理的 Source
    都有条目）；缺失即内部不变量破坏，直接失败（fail loud，不静默产出
    空资产）。
    """

    written: list[Path] = []
    for source in sources:
        units = source_units[source.source_id]
        written.append(write_source_asset(dir_root, source, units))
    (dir_root / "review").mkdir(parents=True, exist_ok=True)
    (dir_root / "derived").mkdir(parents=True, exist_ok=True)
    (dir_root / "review" / ".gitkeep").write_text("", encoding="utf-8")
    (dir_root / "derived" / ".gitkeep").write_text("", encoding="utf-8")
    written.append(write_trusted_set(dir_root, trusted))
    written.append(write_gap_report(dir_root, gaps))
    # 运行摘要最后写：其 asset_organization 清单描述已落盘的完整组织。
    written.append(write_run_summary(dir_root, summary))
    return written
