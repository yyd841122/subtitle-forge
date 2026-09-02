"""Ticket 02 验收：Corpus 批处理——多 Source 顺序完成，互不污染（R1.1、R6.4）。

一次 run 处理 Corpus 内全部 Source：每 Source 各自产出忠实层资产，可信
发布集与运行摘要覆盖全部 Source 且归属正确；任何 Source 的知识单元不出
现在另一 Source 的产物中。断言仍只针对外部产物（Testing Decisions），
资产布局从运行摘要的 asset_organization 自描述清单读取，不硬编码路径。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

from conftest import make_ep02_units, make_units_with_time_range, parse_json_block

from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
)

EP01_UNITS = {"u-001", "u-002", "u-003"}
EP02_UNITS = {"u-101", "u-102", "u-103"}


def batch_roles() -> CognitiveRoles:
    """一个 stub module 覆盖两个 Source：StubExtractor.script 同时含
    ep01、ep02 各自的独立脚本条目（票 02 验收的输入形态）。"""

    return CognitiveRoles(
        extractor=StubExtractor(
            script={"ep01": make_units_with_time_range(), "ep02": make_ep02_units()}
        ),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


def run_batch(
    corpus_dir: Path, tmp_path: Path, roles: CognitiveRoles
) -> tuple[int, Path]:
    """走 CLI 端到端（含落盘），返回（退出码, 资产目录）。"""

    mod = types.ModuleType("batch_stub_roles")
    mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
    sys.modules["batch_stub_roles"] = mod
    from subtitle_forge.cli import main

    asset_dir = tmp_path / "assets"
    rc = main(["run", str(corpus_dir), str(asset_dir), "--stub-module", "batch_stub_roles"])
    return rc, asset_dir


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestCorpusBatchAcceptance:
    def test_two_sources_one_run_assets_in_place(self, two_source_corpus, tmp_path):
        """AC1：两 Source、一个 stub module → 退出码 0；asset_organization
        清单中两个 Source 的忠实层资产各就各位。"""

        rc, asset_dir = run_batch(two_source_corpus, tmp_path, batch_roles())
        assert rc == 0

        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]
        per_source = org["faithful_layer"]["per_source"]
        assert len(per_source) == 2
        source_ids = {
            parse_json_block(asset_dir / rel)["source_id"] for rel in per_source
        }
        assert source_ids == {"ep01", "ep02"}

    def test_faithful_assets_match_own_script_exactly(self, two_source_corpus, tmp_path):
        """AC2：每份忠实层资产的 unit_id 集合与该 Source 的脚本精确一致
        （互不污染：ep01 的单元不出现在 ep02 的资产中，反之亦然）。"""

        _, asset_dir = run_batch(two_source_corpus, tmp_path, batch_roles())
        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]
        by_source = {
            parse_json_block(asset_dir / rel)["source_id"]: {
                u["unit_id"] for u in parse_json_block(asset_dir / rel)["units"]
            }
            for rel in org["faithful_layer"]["per_source"]
        }
        assert by_source == {"ep01": EP01_UNITS, "ep02": EP02_UNITS}

    def test_trusted_set_grouped_by_source(self, two_source_corpus, tmp_path):
        """AC2：trusted-set 按 source_id 分组后分别与两份脚本一致，条目
        总数 = 两组之和；归属正确（segment_id 锚定各自 Source）。"""

        _, asset_dir = run_batch(two_source_corpus, tmp_path, batch_roles())
        trusted = parse_json_block(asset_dir / "trusted-set.md")

        grouped: dict[str, set[str]] = {}
        for e in trusted["entries"]:
            grouped.setdefault(e["source_id"], set()).add(e["unit_id"])
            assert e["source_reference"]["segment_id"].startswith(e["source_id"] + "#")
        assert grouped == {"ep01": EP01_UNITS, "ep02": EP02_UNITS}
        assert len(trusted["entries"]) == len(EP01_UNITS) + len(EP02_UNITS)

    def test_run_summary_both_sources_reconciled(self, two_source_corpus, tmp_path):
        """AC3：两个 Source 均 success、各自单元状态齐全（对账覆盖全部
        Source，A3 运行内部分）；处理顺序为文件名序（票内裁定）；
        gap-report 为空。"""

        _, asset_dir = run_batch(two_source_corpus, tmp_path, batch_roles())
        summary = parse_json_block(asset_dir / "run-summary.md")

        assert [s["source_id"] for s in summary["sources"]] == ["ep01", "ep02"]
        for record in summary["sources"]:
            expected = EP01_UNITS if record["source_id"] == "ep01" else EP02_UNITS
            assert record["status"] == "success"
            assert {u["unit_id"] for u in record["units"]} == expected
            assert all(u["status"] == "passed" for u in record["units"])

        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []


# ---------------------------------------------------------------------------
# 触界行为（明确不含，fail loud——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestBatchBoundaries:
    def test_empty_corpus_still_rejected(self, tmp_path):
        """空 Corpus 仍明确拒绝（语义不变；退出码并入 07 票的全局中止族：
        运行未开始，与「运行完成但部分失败」的退出码 1 机器可辨）。"""

        empty_dir = tmp_path / "empty-corpus"
        empty_dir.mkdir()
        from subtitle_forge.cli import main

        rc = main(["run", str(empty_dir), str(tmp_path / "assets")])
        assert rc == 3


# 02 票触界测试 test_any_source_failure_fails_whole_run（无失败隔离：
# 任一 Source 异常使整次运行失败）随 07 票失败隔离落地退役——隔离
# 语义（该 Source failed、其余照常、退出码 1）由
# test_source_failure_isolation.py 全面验收。
