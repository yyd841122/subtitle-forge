"""端到端接缝测试（Ticket 01 验收）：单 Source 走完 提炼→审查→可信发布 完整路径。

唯一接缝 = Corpus + 认知角色替身 → 资产目录（可信发布集 + 缺口报告）+
运行摘要（Testing Decisions）。断言只针对外部产物及其自描述 schema，
不断言内部结构（阶段函数签名、中间产物格式、目录布局不锁死）。
"""

from __future__ import annotations

import json
import re
import sys
import types
from pathlib import Path

from conftest import (
    SEG_TEXTS,
    make_unit_text_position,
    make_units_with_time_range,
)

from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
    UnitAuditVerdict,
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_and_write(tmp_path: Path, ass_file: Path, roles: CognitiveRoles) -> Path:
    """走 CLI 端到端（含落盘），返回资产目录。"""

    tmp_path.mkdir(parents=True, exist_ok=True)
    asset_dir = tmp_path / "assets"
    mod = types.ModuleType("injected_stub_roles")
    mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
    sys.modules["injected_stub_roles"] = mod
    from subtitle_forge.cli import main

    rc = main(["run", str(ass_file.parent), str(asset_dir), "--stub-module", "injected_stub_roles"])
    assert rc == 0, "端到端运行应成功"
    return asset_dir


def default_roles(units) -> CognitiveRoles:
    return CognitiveRoles(
        extractor=StubExtractor(script={"ep01": units}),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


# ---------------------------------------------------------------------------
# 单 Source 端到端：知识单元走完 提炼→审查→可信发布 的完整可观察路径
# ---------------------------------------------------------------------------


class TestSingleSourceEndToEnd:
    def test_unit_reaches_trusted_set(self, tmp_path, ass_file):
        """提炼替身产出 → 审查替身判定通过 → 出现在可信发布集，运行后可指认。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-001", "u-002", "u-003"}

    def test_source_reference_is_text_plus_locator(self, tmp_path, ass_file):
        """发布集条目 = 陈述 + 原文文本片段 + 定位信息（Segment 锚定）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        for e in trusted["entries"]:
            ref = e["source_reference"]
            assert ref["segment_id"].startswith("ep01#seg")
            assert ref["quoted_text"] in SEG_TEXTS  # 原文文本片段真实取自 Source
            assert ref["locator"]["kind"] == "time_range"
            assert ref["locator"]["start_ms"] < ref["locator"]["end_ms"]

    def test_locator_not_locked_to_time_range(self, tmp_path, ass_file):
        """locator 表达空间保留非时间定位类型（R1.4/Q26 未来兼容约束）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles((make_unit_text_position(),)))
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        loc = trusted["entries"][0]["source_reference"]["locator"]
        assert loc["kind"] == "text_position"
        assert "start_ms" not in loc  # 时间区间不是 locator 的必填字段

    def test_unit_types_beyond_claim(self, tmp_path, ass_file):
        """知识单元类型不限于 Claim：method/conclusion 等均在资产中表达（R2.2）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        types_ = {e["unit_type"] for e in trusted["entries"]}
        assert types_ == {"claim", "method", "conclusion"}


# ---------------------------------------------------------------------------
# 外部产物结构
# ---------------------------------------------------------------------------


class TestExternalArtifacts:
    def test_gap_report_empty_but_structurally_complete(self, tmp_path, ass_file):
        """缺口报告一等产物：无异常时内容为空，结构完整（人可读 + 机可解析）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        report = parse_json_block(asset_dir / "gap-report.md")
        assert report["entries"] == []  # 本次运行无异常
        # 四类缺口类别结构齐全（执行失败/审计拒绝/覆盖存疑/警告）
        assert set(report["categories"]) == {
            "execution_failure",
            "audit_rejection",
            "coverage_concern",
            "warning",
        }
        assert "缺口报告" in read_text(asset_dir / "gap-report.md")  # 人可读

    def test_run_summary_full_reconciliation(self, tmp_path, ass_file):
        """运行摘要：Source 有实体状态（成功），每个知识单元有实体状态（通过）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
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

    def test_entity_status_enums_observable(self, tmp_path, ass_file):
        """状态枚举可表达：通过/拒绝/待复核/失败在运行摘要自描述 schema 中可辨
        （枚举从外部产物观察，不从内部常量断言）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        summary = parse_json_block(asset_dir / "run-summary.md")

        assert set(summary["source_status_values"]) == {"success", "failed", "needs_review"}
        assert set(summary["unit_status_values"]) == {
            "passed",
            "rejected",
            "needs_review",
            "failed",
        }

    def test_human_readable_top_level_artifacts(self, tmp_path, ass_file):
        """人是一级消费者：三类外部产物均含可读标题与说明文字。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        assert "可信发布集" in read_text(asset_dir / "trusted-set.md")
        assert "缺口报告" in read_text(asset_dir / "gap-report.md")
        assert "运行摘要" in read_text(asset_dir / "run-summary.md")


# ---------------------------------------------------------------------------
# 替身按认知角色独立注入并分别设定行为（Testing Decisions 的机制验收）
# 三个角色的行为变化都只从外部产物辨别：
#   提炼       → 可信发布集内容变化
#   推理审计   → 运行摘要单元记录的通过理由变化
#   覆盖审计   → 运行摘要 coverage_audit 结论变化
# ---------------------------------------------------------------------------


class TestRoleStubInjection:
    UNITS = staticmethod(make_units_with_time_range)

    def test_extractor_behavior_varies_artifacts(self, tmp_path, ass_file):
        """提炼替身单独设定行为：脚本产出 3 单元 vs 1 单元，发布集随之不同。"""

        full = run_and_write(tmp_path / "a", ass_file, default_roles(self.UNITS()))
        partial = run_and_write(tmp_path / "b", ass_file, default_roles(self.UNITS()[:1]))
        n_full = len(parse_json_block(full / "trusted-set.md")["entries"])
        n_partial = len(parse_json_block(partial / "trusted-set.md")["entries"])
        assert (n_full, n_partial) == (3, 1)

    def test_inference_auditor_behavior_varies_artifacts(self, tmp_path, ass_file):
        """推理审计替身单独设定行为（提炼脚本不变）：通过结论的理由进入
        运行摘要的单元记录——理由文本即审查角色行为的可观察痕迹。"""

        units = self.UNITS()
        plain = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(default=UnitAuditVerdict(verdict="pass", reason="")),
            coverage_auditor=StubCoverageAuditor(),
        )
        labeled = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(
                default=UnitAuditVerdict(verdict="pass", reason="审查替身受控通过：推理在支持范围内")
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        a = run_and_write(tmp_path / "a", ass_file, plain)
        b = run_and_write(tmp_path / "b", ass_file, labeled)

        sa = parse_json_block(a / "run-summary.md")["sources"][0]["units"]
        sb = parse_json_block(b / "run-summary.md")["sources"][0]["units"]
        # 发布集不变（都是 pass），但审查行为差异在运行摘要可辨
        assert parse_json_block(a / "trusted-set.md") == parse_json_block(b / "trusted-set.md")
        assert all(u["reason"] == "" for u in sa)
        assert all(u["reason"] == "审查替身受控通过：推理在支持范围内" for u in sb)

    def test_coverage_auditor_behavior_varies_artifacts(self, tmp_path, ass_file):
        """覆盖审计替身单独设定行为（其余角色不变）：结论进运行摘要的
        coverage_audit 字段——01 骨架下覆盖良好与否不改变发布集（覆盖
        存疑的缺口语义归 08 票），但结论本身可观察。"""

        units = self.UNITS()
        from subtitle_forge.roles import CoverageVerdict

        good = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        concerned = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(
                verdicts={"ep01": CoverageVerdict(covered=False, reason="受控：疑似遗漏结论性知识")}
            ),
        )
        a = run_and_write(tmp_path / "a", ass_file, good)
        b = run_and_write(tmp_path / "b", ass_file, concerned)

        ca = parse_json_block(a / "run-summary.md")["sources"][0]["coverage_audit"]
        cb = parse_json_block(b / "run-summary.md")["sources"][0]["coverage_audit"]
        assert ca["covered"] is True
        assert cb == {"covered": False, "reason": "受控：疑似遗漏结论性知识"}

    def test_stub_extracts_scripted_units_deterministically(self, tmp_path, ass_file):
        """提炼替身产出完全由脚本决定——确定性（同输入两次运行同输出）。"""

        a = run_and_write(tmp_path / "a", ass_file, default_roles(self.UNITS()[:2]))
        b = run_and_write(tmp_path / "b", ass_file, default_roles(self.UNITS()[:2]))
        assert parse_json_block(a / "trusted-set.md") == parse_json_block(b / "trusted-set.md")


# ---------------------------------------------------------------------------
# 概念边界在资产组织中成立（忠实层/审查层、基础层/衍生层，最小形态）
# 运行摘要自描述资产组织（asset_organization 清单）：测试从该声明读取
# 各层位置后验证边界语义——不硬编码任何路径/目录名，布局变化只改声明。
# ---------------------------------------------------------------------------


class TestLayerBoundaries:
    def test_faithful_layer_holds_source_knowledge_no_system_judgment(
        self, tmp_path, ass_file
    ):
        """忠实层资产：按 Source 存放、忠实表达来源内容、自声明不含系统
        判断（R2.5 最小形态）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        summary = parse_json_block(asset_dir / "run-summary.md")
        org = summary["asset_organization"]

        # 忠实层按 Source 组织：每个 Source 一份资产（从清单读取，非硬编码）
        per_source = org["faithful_layer"]["per_source"]
        assert len(per_source) == 1
        units_doc = parse_json_block(asset_dir / per_source[0])
        assert units_doc["source_id"] == "ep01"
        units_text = read_text(asset_dir / per_source[0])
        assert "忠实层资产" in units_text
        assert "系统判断不写入本文件" in units_text

    def test_review_layer_separate_from_faithful(self, tmp_path, ass_file):
        """审查层独立声明且与忠实层分离（R2.5 最小形态；01 骨架无正式
        Review Note——09 票产出，此处只验证分离的组织边界成立）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]

        review = org["review_layer"]
        assert review["holds"] != org["faithful_layer"]  # 声明为不同职责
        assert "系统判断" in review["holds"]
        assert (asset_dir / review["path"]).is_dir()
        # 忠实层资产不在审查层路径下（分离成立）
        faithful_paths = org["faithful_layer"]["per_source"]
        assert all(not str(p).startswith(str(review["path"])) for p in faithful_paths)

    def test_derived_layer_separate_and_recomputable_declaration(
        self, tmp_path, ass_file
    ):
        """衍生层独立声明、可整体重算，与基础层（每 Source 资产）分离
        （R2.6 最小形态）。"""

        asset_dir = run_and_write(tmp_path, ass_file, default_roles(make_units_with_time_range()))
        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]

        derived = org["derived_layer"]
        assert (asset_dir / derived["path"]).is_dir()
        assert "重算" in derived["holds"]
        faithful_paths = org["faithful_layer"]["per_source"]
        assert all(not str(p).startswith(str(derived["path"])) for p in faithful_paths)
