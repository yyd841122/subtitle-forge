"""Ticket 03 验收：审计拒绝的下落——单元级拒绝成立（R3.5、R4.2、A2、A4）。

A2 场景（推理审计）：单元带真实存在于原文的引用，但陈述明显越界
（引用只讲阶乘的基准情形，断言却推广为一切递归函数的基准情形）。
推理审查替身因此对该 unit_id 预设 reject + 理由。被拒单元不进可信
发布集；缺口报告出现 audit_rejection 条目（含 Source、指向单元、
原因、下落）；运行摘要该单元 rejected；含被拒单元的 Source 仍为
success（A4：全部单元有明确下落即成功）。断言只针对外部产物
（Testing Decisions）。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from conftest import make_units_a2_overreach, make_units_with_time_range, parse_json_block

from subtitle_forge.model import KnowledgeUnit
from subtitle_forge.pipeline import OutOfScopeVerdictError
from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
    UnitAuditVerdict,
)

REJECT_REASON = (
    "引用仅陈述阶乘以 n 等于零返回一为基准情形，"
    "断言却推广为一切递归函数的基准情形，超出引用支持范围"
)


def rejecting_roles() -> CognitiveRoles:
    """A2 场景的认知角色集：提炼脚本产出含越界单元的候选集，推理审计
    替身对 u-002 预设 reject + 理由，其余单元默认通过。"""

    return CognitiveRoles(
        extractor=StubExtractor(script={"ep01": make_units_a2_overreach()}),
        inference_auditor=StubInferenceAuditor(
            verdicts={"u-002": UnitAuditVerdict(verdict="reject", reason=REJECT_REASON)}
        ),
        coverage_auditor=StubCoverageAuditor(),
    )


def run_and_write(tmp_path: Path, ass_file: Path, roles: CognitiveRoles) -> Path:
    """走 CLI 端到端（含落盘），返回资产目录。"""

    tmp_path.mkdir(parents=True, exist_ok=True)
    asset_dir = tmp_path / "assets"
    mod = types.ModuleType("reject_stub_roles")
    mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
    sys.modules["reject_stub_roles"] = mod
    from subtitle_forge.cli import main

    rc = main(["run", str(ass_file.parent), str(asset_dir), "--stub-module", "reject_stub_roles"])
    assert rc == 0, "含被拒单元的运行应成功（A4：全部单元有明确下落即成功）"
    return asset_dir


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestAuditRejectionAcceptance:
    def test_rejected_unit_absent_from_trusted_set(self, tmp_path, ass_file):
        """AC1：A2 fixture（真实引用 + 越界陈述，替身预设 reject）→
        被拒单元不出现在可信发布集，其余单元照常进入。"""

        asset_dir = run_and_write(tmp_path, ass_file, rejecting_roles())
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-001", "u-003"}

    def test_gap_report_records_audit_rejection(self, tmp_path, ass_file):
        """AC2：缺口报告含 audit_rejection 条目——category / source_id /
        subject（指向单元）/ reason（替身拒绝理由）/ outcome（下落）。"""

        asset_dir = run_and_write(tmp_path, ass_file, rejecting_roles())
        report = parse_json_block(asset_dir / "gap-report.md")
        assert report["entries"] == [
            {
                "category": "audit_rejection",
                "source_id": "ep01",
                "subject": "u-002",
                "reason": REJECT_REASON,
                "outcome": "不进入发布集，记录在案",
            }
        ]

    def test_run_summary_rejected_unit_source_success(self, tmp_path, ass_file):
        """AC3：运行摘要该单元 rejected（含拒绝理由）；Source 仍 success
        （A4：Source 级无拒绝，被拒单元不妨碍成功）；同 Source 其余单元
        照常 passed，不受影响。"""

        asset_dir = run_and_write(tmp_path, ass_file, rejecting_roles())
        summary = parse_json_block(asset_dir / "run-summary.md")

        assert len(summary["sources"]) == 1
        src = summary["sources"][0]
        assert src["source_id"] == "ep01"
        assert src["status"] == "success"
        unit_records = {u["unit_id"]: u for u in src["units"]}
        assert {uid: u["status"] for uid, u in unit_records.items()} == {
            "u-001": "passed",
            "u-002": "rejected",
            "u-003": "passed",
        }
        assert unit_records["u-002"]["reason"] == REJECT_REASON

    def test_rejected_unit_stays_in_faithful_layer(self, tmp_path, ass_file):
        """被拒单元仍是提炼产物，留在忠实层资产（R2.5：审查结果不改
        忠实层；审计门只决定发布集成员资格）。资产路径从运行摘要的
        asset_organization 自描述清单读取，不硬编码。"""

        asset_dir = run_and_write(tmp_path, ass_file, rejecting_roles())
        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]
        units_doc = parse_json_block(asset_dir / org["faithful_layer"]["per_source"][0])
        assert {u["unit_id"] for u in units_doc["units"]} == {"u-001", "u-002", "u-003"}

    def test_source_with_all_units_rejected_still_success(self, tmp_path, ass_file):
        """A4 边界：Source 内全部单元被拒 → 发布集为空、缺口条目逐单元
        留痕，Source 仍 success——被拒但已记录的知识单元不妨碍成功。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_with_time_range()}),
            inference_auditor=StubInferenceAuditor(
                default=UnitAuditVerdict(verdict="reject", reason="受控：整源拒绝")
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert {e["subject"] for e in entries} == {"u-001", "u-002", "u-003"}
        assert all(e["category"] == "audit_rejection" for e in entries)
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "success"
        assert all(u["status"] == "rejected" for u in src["units"])

    def test_reject_takes_precedence_over_missing_reference(self, tmp_path, ass_file):
        """票内裁定（优先序）：被拒且无引用的单元走拒绝下落——审计拒绝
        本身是完整下落（不进发布集 + 留痕，R2.4 已满足），不因缺引用再
        挡板；missing_source_reference 挡板只守"通过"路径。"""

        no_ref_unit = KnowledgeUnit(
            unit_id="u-noref-rejected",
            unit_type="claim",
            statement="基准情形使递归终止",
            source_reference=None,
        )
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": (no_ref_unit,)}),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-noref-rejected": UnitAuditVerdict(verdict="reject", reason="受控：拒绝无引用单元")
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [e["subject"] for e in entries] == ["u-noref-rejected"]
        assert entries[0]["category"] == "audit_rejection"
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "success"
        assert src["units"][0]["status"] == "rejected"


# ---------------------------------------------------------------------------
# 触界行为（明确不含，fail loud——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestAuditRejectionBoundaries:
    def test_reject_without_reason_fails_loud(self, tmp_path, ass_file):
        """A11 守卫：拒绝结论不带可读理由（空或纯空白）→ 缺口条目将缺
        "原因"，属角色契约破坏，fail loud（不产出语义不完整的条目）。"""

        for blank_reason in ("", "   "):
            roles = CognitiveRoles(
                extractor=StubExtractor(script={"ep01": make_units_with_time_range()[:1]}),
                inference_auditor=StubInferenceAuditor(
                    verdicts={"u-001": UnitAuditVerdict(verdict="reject", reason=blank_reason)}
                ),
                coverage_auditor=StubCoverageAuditor(),
            )
            mod = types.ModuleType("silent_reject_stub_roles")
            mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
            sys.modules["silent_reject_stub_roles"] = mod
            from subtitle_forge.cli import main

            with pytest.raises(ValueError, match="u-001.*缺少理由"):
                main(["run", str(ass_file.parent), str(tmp_path / "assets"),
                      "--stub-module", "silent_reject_stub_roles"])

    def test_inconclusive_not_recorded_as_audit_rejection(self, tmp_path, ass_file):
        """触界（05 票语义落地后的 03 界线）：不确定结论的单元走待复核
        下落（运行摘要 needs_review），不留 audit_rejection 条目——拒绝
        与待复核不得混用（R4.6），拒绝机制只处置"拒绝"结论。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_with_time_range()[:1]}),
            inference_auditor=StubInferenceAuditor(
                verdicts={"u-001": UnitAuditVerdict(verdict="inconclusive", reason="受控：无法可靠判定")}
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["units"][0]["status"] == "needs_review"

    def test_missing_reference_still_fails_loud(self, tmp_path, ass_file):
        """无 Source Reference 单元的下落不属本票（06 票）：通过结论 +
        无引用单元 → 显式挡板抛错，挡板保留。"""

        no_ref_unit = KnowledgeUnit(
            unit_id="u-noref",
            unit_type="claim",
            statement="基准情形使递归终止",
            source_reference=None,
        )
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": (no_ref_unit,)}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        mod = types.ModuleType("noref_stub_roles")
        mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
        sys.modules["noref_stub_roles"] = mod
        from subtitle_forge.cli import main

        with pytest.raises(OutOfScopeVerdictError, match="u-noref.*missing_source_reference"):
            main(["run", str(ass_file.parent), str(tmp_path / "assets"),
                  "--stub-module", "noref_stub_roles"])
