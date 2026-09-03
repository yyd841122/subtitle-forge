"""Ticket 09 验收：运行范围控制（指定 Source 子集）（R5.1/R5.2、A7 触发形态、A12 控制手段）。

运行请求可用 ``--source id[,id…]`` 指定 Source 子集：仅被选 Source 被处理，
未选 Source 本次完全不触碰——忠实层资产不创建、解析观察不产生。范围控制
由此成为可观察的成本控制手段（A12）。验收全部限定**全新资产目录**（票面）：
对已有资产目录的范围运行是本票触界——明确拒绝（fail loud），不固化与
R4.3/A3 相抵的临时语义。断言只针对外部产物（Testing Decisions）。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from conftest import (
    ASS_CONTENT_MALFORMED,
    ASS_CONTENT,
    make_ep02_units,
    make_ep03_units,
    make_units_with_time_range,
    parse_json_block,
)

from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
)

EP01_UNITS = {"u-001", "u-002", "u-003"}
EP02_UNITS = {"u-101", "u-102", "u-103"}
EP03_UNITS = {"u-201", "u-202", "u-203"}

STUB_MODULE = "scope_stub_roles"


def scope_roles() -> CognitiveRoles:
    """一个 stub module 覆盖三个 Source（与批处理测试同形态的受控输入）。"""

    return CognitiveRoles(
        extractor=StubExtractor(
            script={
                "ep01": make_units_with_time_range(),
                "ep02": make_ep02_units(),
                "ep03": make_ep03_units(),
            }
        ),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


def run_run(
    corpus_dir: Path,
    asset_dir: Path,
    selection: str | None = None,
    roles: CognitiveRoles | None = None,
) -> int:
    """走 CLI 端到端（含落盘），``selection`` 非空时加 ``--source``。"""

    mod = types.ModuleType(STUB_MODULE)
    mod.stub_roles = lambda: roles or scope_roles()  # type: ignore[attr-defined]
    sys.modules[STUB_MODULE] = mod
    from subtitle_forge.cli import main

    argv = ["run", str(corpus_dir), str(asset_dir), "--stub-module", STUB_MODULE]
    if selection is not None:
        argv += ["--source", selection]
    return main(argv)


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物；全部限定全新资产目录）
# ---------------------------------------------------------------------------


class TestRunScopeAcceptance:
    def test_selection_of_one_processes_only_it(self, three_source_corpus, tmp_path):
        """AC1/AC2：三 Source 选其一、全新资产目录 → 仅其被处理：运行摘要
        以该 Source 为本次资产版本的全部实体（状态齐全、单元下落齐全、
        无缺席者）；其余 Source 的忠实层资产未被创建。资产布局从运行
        摘要的 asset_organization 清单读取（Testing Decisions：不锁死
        目录布局；清单由目录现状生成，清单外即磁盘上未创建）。"""

        asset_dir = tmp_path / "assets"
        rc = run_run(three_source_corpus, asset_dir, selection="ep02")
        assert rc == 0

        summary = parse_json_block(asset_dir / "run-summary.md")
        assert [s["source_id"] for s in summary["sources"]] == ["ep02"]
        record = summary["sources"][0]
        assert record["status"] == "success"
        assert {u["unit_id"] for u in record["units"]} == EP02_UNITS
        assert all(u["status"] == "passed" for u in record["units"])

        org = summary["asset_organization"]
        advertised = {
            parse_json_block(asset_dir / rel)["source_id"]
            for rel in org["faithful_layer"]["per_source"]
        }
        assert advertised == {"ep02"}

        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["source_id"] for e in trusted["entries"]} == {"ep02"}
        assert {e["unit_id"] for e in trusted["entries"]} == EP02_UNITS

    def test_selection_of_multiple_covers_all_selected(self, three_source_corpus, tmp_path):
        """多选：选中的 Source 全部被处理，批内顺序仍为文件名序（02 票
        裁定——选择是成员资格，不重排处理顺序）；未选者不出现。"""

        asset_dir = tmp_path / "assets"
        rc = run_run(three_source_corpus, asset_dir, selection="ep03,ep01")
        assert rc == 0

        summary = parse_json_block(asset_dir / "run-summary.md")
        assert [s["source_id"] for s in summary["sources"]] == ["ep01", "ep03"]
        assert all(s["status"] == "success" for s in summary["sources"])
        by_source = {
            s["source_id"]: {u["unit_id"] for u in s["units"]} for s in summary["sources"]
        }
        assert by_source == {"ep01": EP01_UNITS, "ep03": EP03_UNITS}
        org = summary["asset_organization"]
        advertised = {
            parse_json_block(asset_dir / rel)["source_id"]
            for rel in org["faithful_layer"]["per_source"]
        }
        assert advertised == {"ep01", "ep03"}

    def test_unknown_source_id_clear_error(self, three_source_corpus, tmp_path, capsys):
        """AC3：选不存在的 id → 明确报错（退出码 3：运行未开始的全局中止
        族，与空 Corpus 拒绝同族）、stderr 可辨、资产目录未被创建。"""

        asset_dir = tmp_path / "assets"
        rc = run_run(three_source_corpus, asset_dir, selection="epXX")
        captured = capsys.readouterr()

        assert rc == 3
        assert "epXX" in captured.err
        assert not asset_dir.exists()

    def test_unknown_id_among_valid_ids_rejected(self, three_source_corpus, tmp_path):
        """混合选择（含一个未知 id）整体拒绝——范围请求要么整体成立、
        要么不开始（不静默降级为「处理存在的那些」）。"""

        asset_dir = tmp_path / "assets"
        rc = run_run(three_source_corpus, asset_dir, selection="ep01,epXX")
        assert rc == 3
        assert not asset_dir.exists()

    def test_unselected_source_parse_observations_not_emitted(
        self, tmp_path, capsys
    ):
        """未选 Source 本次完全不触碰：其解析观察（08 票 warning）不产生
        ——ep02 含畸形行，范围运行只选 ep01，缺口报告不出现 ep02 的任何
        条目（对照：全量运行会产生）。"""

        corpus_dir = tmp_path / "corpus-mixed"
        corpus_dir.mkdir()
        (corpus_dir / "ep01.ass").write_text(ASS_CONTENT, encoding="utf-8")
        (corpus_dir / "ep02.ass").write_text(ASS_CONTENT_MALFORMED, encoding="utf-8")

        asset_dir = tmp_path / "assets"
        rc = run_run(corpus_dir, asset_dir, selection="ep01")
        assert rc == 0

        gaps = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [e for e in gaps if e["source_id"] == "ep02"] == []


# ---------------------------------------------------------------------------
# 触界行为（明确不含，fail loud——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestRunScopeBoundaries:
    def test_scoped_run_into_existing_asset_dir_rejected(
        self, three_source_corpus, tmp_path, capsys
    ):
        """触界：对已有资产目录的范围运行明确拒绝（fail loud）。「未选
        Source 引用既有产出」的运行摘要表达由后续票落定后自然开放，本票
        不固化与 R4.3/A3 相抵的临时语义。拒绝不改动任何既有产物。"""

        asset_dir = tmp_path / "assets"
        assert run_run(three_source_corpus, asset_dir) == 0  # 先全量运行建目录

        snapshot = {
            str(p.relative_to(asset_dir)): p.read_bytes()
            for p in sorted(asset_dir.rglob("*"))
            if p.is_file()
        }
        rc = run_run(three_source_corpus, asset_dir, selection="ep01")
        captured = capsys.readouterr()

        assert rc == 3
        assert captured.err.strip()
        after = {
            str(p.relative_to(asset_dir)): p.read_bytes()
            for p in sorted(asset_dir.rglob("*"))
            if p.is_file()
        }
        assert after == snapshot

    def test_malformed_selection_usage_error(self, three_source_corpus, tmp_path, capsys):
        """畸形选择（空值 / 空 token）是用法错误（argparse 标准，退出码 2）：
        解析层即拒绝，不进入运行；资产目录未被创建。"""

        for selection in ("", "ep01,,ep02"):
            asset_dir = tmp_path / f"assets-{selection.count(',')}"
            with pytest.raises(SystemExit) as exc_info:
                run_run(three_source_corpus, asset_dir, selection=selection)
            assert exc_info.value.code == 2
            capsys.readouterr()
            assert not asset_dir.exists()
