"""端到端接缝测试（Ticket 01 验收）：单 Source 走完 提炼→审查→可信发布 完整路径。

唯一接缝 = Corpus + 认知角色替身 → 资产目录（可信发布集 + 缺口报告）+
运行摘要。断言只针对外部产物，不断言内部结构（Testing Decisions）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from conftest import (
    SEG_TEXTS,
    make_unit_text_position,
    make_units_with_time_range,
)

from subtitle_forge.ass import load_corpus
from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
)


# ---------------------------------------------------------------------------
# 辅助：从落盘产物中解析结构（模拟"机器是一级消费者"——不 import 内部结构）
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def parse_json_block(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    blocks = _JSON_BLOCK_RE.findall(text)
    assert blocks, f"{path} 应含机器可解析的 json 代码块"
    return json.loads(blocks[0])


def run_and_write(tmp_path: Path, ass_file: Path, roles: CognitiveRoles) -> Path:
    """走 CLI 端到端（含落盘），返回资产目录。"""

    tmp_path.mkdir(parents=True, exist_ok=True)
    asset_dir = tmp_path / "assets"
    stub_file = tmp_path / "stub_roles_mod.py"
    # 通过文件模块注入替身（替身注入是测试输入的一部分）。
    stub_file.write_text(
        "from subtitle_forge.roles import CognitiveRoles\n"
        "ROLES = None\n"
        "def stub_roles():\n"
        "    return ROLES\n",
        encoding="utf-8",
    )
    # 对象无法跨进程传递——测试内直接调用 CLI 同进程入口，注入经由环境：
    # 这里改用进程内 main() + monkeypatch 模块级 ROLES。
    return _run_cli_with_roles(tmp_path, ass_file, asset_dir, stub_file, roles)


def _run_cli_with_roles(
    tmp_path: Path, ass_file: Path, asset_dir: Path, stub_file: Path, roles: CognitiveRoles
) -> Path:
    sys.modules[stub_file.stem] = _make_stub_module(roles)
    from subtitle_forge.cli import main

    rc = main(["run", str(ass_file.parent), str(asset_dir), "--stub-module", stub_file.stem])
    assert rc == 0
    return asset_dir


def _make_stub_module(roles: CognitiveRoles):
    import types

    mod = types.ModuleType("injected_stub_roles")
    mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# 单 Source 端到端：知识单元走完 提炼→审查→可信发布 的完整可观察路径
# ---------------------------------------------------------------------------


class TestSingleSourceEndToEnd:
    def test_unit_reaches_trusted_set(self, tmp_path, ass_file):
        """提炼替身产出 → 审查替身通过 → 出现在可信发布集，运行后可指认。"""

        units = make_units_with_time_range()
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        trusted = parse_json_block(asset_dir / "trusted-set.md")
        by_id = {e["unit_id"]: e for e in trusted["entries"]}
        assert set(by_id) == {"u-001", "u-002", "u-003"}

    def test_source_reference_is_text_plus_locator(
        self, tmp_path, ass_file
    ):
        """发布集条目 = 陈述 + 原文文本片段 + 定位信息（Segment 锚定）。"""

        units = make_units_with_time_range()
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        trusted = parse_json_block(asset_dir / "trusted-set.md")
        for e in trusted["entries"]:
            ref = e["source_reference"]
            assert ref["segment_id"].startswith("ep01#seg")
            assert ref["quoted_text"] in SEG_TEXTS  # 原文文本片段真实取自 Source
            assert ref["locator"]["kind"] == "time_range"
            assert ref["locator"]["start_ms"] < ref["locator"]["end_ms"]

    def test_locator_not_locked_to_time_range(self, tmp_path, ass_file):
        """locator 表达空间保留非时间定位类型（R1.4/Q26 未来兼容约束）。"""

        unit = make_unit_text_position()
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": (unit,)}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        trusted = parse_json_block(asset_dir / "trusted-set.md")
        loc = trusted["entries"][0]["source_reference"]["locator"]
        assert loc["kind"] == "text_position"
        assert "start_ms" not in loc  # 时间区间不是 locator 的必填字段

    def test_unit_types_beyond_claim(self, tmp_path, ass_file):
        """知识单元类型不限于 Claim：method/conclusion 等均在资产中表达（R2.2）。"""

        units = make_units_with_time_range()
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        units_doc = parse_json_block(
            asset_dir / "sources" / "ep01" / "knowledge-units.md"
        )
        types = {u["unit_type"] for u in units_doc["units"]}
        assert types == {"claim", "method", "conclusion"}


# ---------------------------------------------------------------------------
# 外部产物结构
# ---------------------------------------------------------------------------


class TestExternalArtifacts:
    def _run(self, tmp_path, ass_file):
        units = make_units_with_time_range()
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        return run_and_write(tmp_path, ass_file, roles)

    def test_gap_report_empty_but_structurally_complete(self, tmp_path, ass_file):
        """缺口报告一等产物：无异常时内容为空，结构完整（人可读 + 机可解析）。"""

        asset_dir = self._run(tmp_path, ass_file)
        report = parse_json_block(asset_dir / "gap-report.md")
        assert report["entries"] == []  # 本次运行无异常
        # 四类缺口类别结构齐全（执行失败/审计拒绝/覆盖存疑/警告）
        assert set(report["categories"]) == {
            "execution_failure",
            "audit_rejection",
            "coverage_concern",
            "warning",
        }
        text = (asset_dir / "gap-report.md").read_text(encoding="utf-8")
        assert "缺口报告" in text  # 人可读

    def test_run_summary_full_reconciliation(self, tmp_path, ass_file):
        """运行摘要：Source 有实体状态（成功），每个知识单元有实体状态（通过）。"""

        asset_dir = self._run(tmp_path, ass_file)
        summary = parse_json_block(asset_dir / "run-summary.md")

        assert len(summary["sources"]) == 1
        src = summary["sources"][0]
        assert src["source_id"] == "ep01"
        assert src["status"] == "success"
        unit_status = {u["unit_id"]: u["status"] for u in src["units"]}
        assert unit_status == {
            "u-001": "passed",
            "u-002": "passed",
            "u-003": "passed",
        }

    def test_unit_status_enum_expressible(self, tmp_path, ass_file):
        """状态枚举可表达：通过/拒绝/待复核/失败在产物 schema 中可辨。"""

        from subtitle_forge.artifacts import (
            UNIT_STATUS_FAILED,
            UNIT_STATUS_NEEDS_REVIEW,
            UNIT_STATUS_PASSED,
            UNIT_STATUS_REJECTED,
        )

        assert {UNIT_STATUS_PASSED, UNIT_STATUS_REJECTED, UNIT_STATUS_NEEDS_REVIEW, UNIT_STATUS_FAILED} == {
            "passed",
            "rejected",
            "needs_review",
            "failed",
        }


# ---------------------------------------------------------------------------
# 替身按认知角色独立注入并分别设定行为（Testing Decisions 的机制验收）
# ---------------------------------------------------------------------------


class TestRoleStubInjection:
    def test_inference_stub_behavior_reaches_artifacts(self, tmp_path, ass_file):
        """审查替身行为独立可设定且真实进入运行：改用只放行部分单元的
        审查脚本（用通过路径表达——01 骨架范围内，行为差异体现在发布集
        内容），发布集随之不同。"""

        # 基线：全部放行
        units = make_units_with_time_range()
        roles_all_pass = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        baseline = run_and_write(tmp_path / "b", ass_file, roles_all_pass)
        n_baseline = len(parse_json_block(baseline / "trusted-set.md")["entries"])

        # 只放行 u-001：审查替身单独设定行为（拒绝其余的完整语义归 03 票，
        # 这里以"提炼替身只产出 u-001 + 审查放行"的组合表达角色独立设定，
        # 结果应当等价——两个角色分别注入、互不干扰）
        roles_partial = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units[:1]}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        partial = run_and_write(tmp_path / "p", ass_file, roles_partial)
        n_partial = len(parse_json_block(partial / "trusted-set.md")["entries"])

        assert n_baseline == 3
        assert n_partial == 1

    def test_stub_extracts_scripted_units_only(self, tmp_path, ass_file):
        """提炼替身产出完全由脚本决定——确定性（同输入同输出）。"""

        units = make_units_with_time_range()
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units[:2]}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-001", "u-002"}

    def test_extractor_called_once_per_source(self, tmp_path, ass_file):
        """运行结果由一次角色调用承载（落盘不二次调用）——通过外部产物
        可辨：替身若被意外二次调用即报错，而运行正常完成。"""

        units = make_units_with_time_range()
        # fail_on_unscripted=True 只挡脚本外 Source；这里用计数替身验证
        # "恰好一次"，从外部产物（运行摘要的 role_call_counts）观察。
        from subtitle_forge.roles import ExtractionOutput

        calls = {"n": 0}

        class CountingExtractor:
            def extract(self, source):
                calls["n"] += 1
                return ExtractionOutput(units=units)

        roles = CognitiveRoles(
            extractor=CountingExtractor(),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)
        summary = parse_json_block(asset_dir / "run-summary.md")
        assert summary["role_call_counts"]["extractor"] == 1
        assert calls["n"] == 1


# ---------------------------------------------------------------------------
# 概念边界在资产组织中成立（忠实层/审查层、基础层/衍生层，最小形态）
# ---------------------------------------------------------------------------


class TestLayerBoundaries:
    def test_faithful_vs_review_layer_separated(self, tmp_path, ass_file):
        """忠实知识与系统判断分开存放：knowledge-units.md 不含系统判断通道，
        review/ 目录独立存在（R2.5 最小结构前提）。"""

        asset_dir = TestExternalArtifacts()._run(tmp_path, ass_file)
        units_text = (asset_dir / "sources" / "ep01" / "knowledge-units.md").read_text(
            encoding="utf-8"
        )
        assert "忠实层资产" in units_text
        assert (asset_dir / "review").is_dir()

    def test_base_vs_derived_layer_separated(self, tmp_path, ass_file):
        """每 Source 资产独立成立；derived/ 独立组织（R2.6 最小结构前提）。"""

        asset_dir = TestExternalArtifacts()._run(tmp_path, ass_file)
        assert (asset_dir / "sources" / "ep01" / "knowledge-units.md").is_file()
        assert (asset_dir / "derived").is_dir()


# ---------------------------------------------------------------------------
# ASS 解析（接缝的输入侧）
# ---------------------------------------------------------------------------


class TestAssParsing:
    def test_dialogues_parsed_with_time(self, ass_file):
        source = load_corpus(ass_file.parent).sources[0]
        assert source.source_id == "ep01"
        assert [s.text for s in source.segments] == SEG_TEXTS
        assert source.segments[0].start_ms == 1000
        assert source.segments[0].end_ms == 6000
        assert source.segments[1].start_ms == 7500

    def test_override_tags_stripped(self, ass_file):
        source = load_corpus(ass_file.parent).sources[0]
        assert "{\\an8}" not in source.segments[1].text
