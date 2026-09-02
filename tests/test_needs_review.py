"""Ticket 05 验收：待复核（inconclusive）语义——单元级未决结论的完整
下落（R4.4、R4.6、A14）。

推理审计替身对某单元返回 inconclusive + 理由（A14 场景：引用真实存在，
但推理上无法可靠判定陈述是否超出引用支持范围）→ 该单元实体状态
needs_review、不进可信发布集、运行摘要记录明确理由（理由文本来自替身
结论本身——R4.4 严格语义：无法可靠判定，非低质量兜底）；该 Source
整体 needs_review（R4.6：存在未获最终结论、需后续人工或系统判断的
问题，尚不能视为完全 settled）。票内裁定：needs_review 单元不进缺口
报告（A14 只要求运行摘要有下落；缺口报告只记异常与缺口，且 R4.6
要求拒绝与待复核不混用）；任一单元 needs_review ⇒ Source needs_review。
断言只针对外部产物（Testing Decisions）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import (
    make_units_a14_inconclusive,
    make_units_with_time_range,
    parse_json_block,
    run_cli_with_roles,
)

from subtitle_forge.model import KnowledgeUnit
from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
    UnitAuditVerdict,
)

# 替身的不确定结论理由：表达 R4.4 的严格语义——原文分别提到基准情形
# 与递归深度有限、从未表述二者的因果联系，"无法可靠判定该通过还是
# 拒绝"（解释性未决，非低质量）；运行摘要的 reason 必须逐字来自它
# （AC2 断言来源，不是系统兜底措辞）。
INCONCLUSIVE_REASON = (
    "原文分别提到基准情形的写法与递归深度必须有限，但未直接表述二者的"
    "因果关系，无法可靠判定该断言是原文隐含的结论还是超出范围的推广"
)


def inconclusive_roles() -> CognitiveRoles:
    """A14 场景的认知角色集：提炼脚本产出"引用真实但推理未决"的候选集，
    推理审计替身对 u-002 预设 inconclusive + 理由，其余单元默认通过。"""

    return CognitiveRoles(
        extractor=StubExtractor(script={"ep01": make_units_a14_inconclusive()}),
        inference_auditor=StubInferenceAuditor(
            verdicts={"u-002": UnitAuditVerdict(verdict="inconclusive", reason=INCONCLUSIVE_REASON)}
        ),
        coverage_auditor=StubCoverageAuditor(),
    )


def run_cli(
    ass_file_or_dir: Path,
    asset_dir: Path,
    roles: CognitiveRoles,
    module_name: str = "needs_review_stub_roles",
) -> int:
    """注册替身模块并执行 CLI，返回退出码（不断言结果——供预期非零或
    预期抛错的触界测试复用同一注册路径；共享通道，见 conftest）。"""

    return run_cli_with_roles(ass_file_or_dir, asset_dir, roles, module_name)


def run_and_write(tmp_path: Path, ass_file: Path, roles: CognitiveRoles) -> Path:
    """走 CLI 端到端（含落盘），返回资产目录。"""

    tmp_path.mkdir(parents=True, exist_ok=True)
    asset_dir = tmp_path / "assets"
    rc = run_cli(ass_file, asset_dir, roles)
    # 待复核是实体状态不是运行失败（R4.6：Source 失败 = 流程无法完整
    # 完成；含未决单元的运行完整结束、全部单元有下落），运行应成功。
    assert rc == 0, "含待复核单元的运行应成功（needs_review 是实体状态，非运行失败）"
    return asset_dir


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestNeedsReviewAcceptance:
    def test_inconclusive_unit_absent_from_trusted_set(self, tmp_path, ass_file):
        """AC1：A14 fixture（真实引用 + 推理未决，替身预设 inconclusive）
        → 该单元不出现在可信发布集，其余单元照常进入。"""

        asset_dir = run_and_write(tmp_path, ass_file, inconclusive_roles())
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-001", "u-003"}

    def test_run_summary_records_stub_reason_verbatim(self, tmp_path, ass_file):
        """AC2：运行摘要该单元 needs_review 且 reason 非空——逐字等于替身
        结论的理由（来源断言：不是系统生成的兜底措辞，R4.4/A14）。"""

        asset_dir = run_and_write(tmp_path, ass_file, inconclusive_roles())
        summary = parse_json_block(asset_dir / "run-summary.md")
        unit_records = {u["unit_id"]: u for u in summary["sources"][0]["units"]}
        assert unit_records["u-002"]["status"] == "needs_review"
        reason = unit_records["u-002"]["reason"]
        assert reason  # 非空（A14：待复核有明确理由记录）
        assert reason == INCONCLUSIVE_REASON  # 理由来自替身结论，非兜底措辞

    def test_source_needs_review_others_unaffected(self, tmp_path, ass_file):
        """AC3：Source 整体 needs_review（票内裁定：任一单元 needs_review
        ⇒ Source needs_review；R4.6 存在未获最终结论的问题）；同 Source
        其余单元照常 passed，不受影响。Source 级 reason 指名待复核单元
        （可解释：未决问题是谁一目了然）。"""

        asset_dir = run_and_write(tmp_path, ass_file, inconclusive_roles())
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["source_id"] == "ep01"
        assert src["status"] == "needs_review"
        assert {u["unit_id"]: u["status"] for u in src["units"]} == {
            "u-001": "passed",
            "u-002": "needs_review",
            "u-003": "passed",
        }
        assert "u-002" in src["reason"] and src["reason"].strip()


# ---------------------------------------------------------------------------
# 行为语义（票内裁定与 Spec 条款的可观察化）
# ---------------------------------------------------------------------------


class TestNeedsReviewBehavior:
    def test_needs_review_unit_not_in_gap_report(self, tmp_path, ass_file):
        """票内裁定（默认不进缺口报告）：A14 只要求运行摘要有下落；缺口
        报告只记异常与缺口（裁决 6），needs_review 是"未决"而非异常；且
        R4.6 要求拒绝与待复核不混用——audit_rejection 条目只属拒绝。"""

        asset_dir = run_and_write(tmp_path, ass_file, inconclusive_roles())
        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []

    def test_needs_review_unit_stays_in_faithful_layer(self, tmp_path, ass_file):
        """待复核单元仍是提炼产物，留在忠实层资产（R2.5：审查结果不改
        忠实层；审计门只决定发布集成员资格）。资产路径从运行摘要的
        asset_organization 自描述清单读取，不硬编码。"""

        asset_dir = run_and_write(tmp_path, ass_file, inconclusive_roles())
        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]
        units_doc = parse_json_block(asset_dir / org["faithful_layer"]["per_source"][0])
        assert {u["unit_id"] for u in units_doc["units"]} == {"u-001", "u-002", "u-003"}

    def test_reject_and_inconclusive_coexist_single_disposition(self, tmp_path, ass_file):
        """混合下落（单单元单条）：被拒单元走拒绝下落（缺口条目 +
        rejected），待复核单元走待复核下落（摘要 needs_review，无缺口
        条目）——两者不混用（R4.6）；Source 因存在未决问题整体
        needs_review（被拒单元是已决下落，不妨碍 needs_review，正如它
        不妨碍 success——A4）。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_with_time_range()}),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-001": UnitAuditVerdict(
                        verdict="reject", reason="受控：引用只讲递归结构，拒绝其推广"
                    ),
                    "u-002": UnitAuditVerdict(verdict="inconclusive", reason=INCONCLUSIVE_REASON),
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]} == {
            "u-003"
        }
        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [e["subject"] for e in entries] == ["u-001"]  # 只有拒绝留条目
        assert entries[0]["category"] == "audit_rejection"
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "needs_review"
        assert {u["unit_id"]: u["status"] for u in src["units"]} == {
            "u-001": "rejected",
            "u-002": "needs_review",
            "u-003": "passed",
        }

    def test_all_units_needs_review_source_needs_review(self, tmp_path, ass_file):
        """边界对照（与 03 票"整源被拒仍 success"并排）：Source 内全部
        单元待复核 → 发布集为空、缺口报告无条目、Source needs_review
        ——未决问题使 Source 尚不能视为 settled（R4.6），这与"全部已决
        （拒绝也是明确下落）即 success"形成语义对照。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_with_time_range()}),
            inference_auditor=StubInferenceAuditor(
                default=UnitAuditVerdict(verdict="inconclusive", reason="受控：整源无法可靠判定")
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "needs_review"
        assert all(u["status"] == "needs_review" for u in src["units"])

    def test_second_source_unaffected_by_needs_review(self, tmp_path, two_source_corpus):
        """跨 Source 隔离：ep01 含待复核单元、ep02 全通过 → 只有 ep01
        needs_review，ep02 照常 success 且其单元照常进发布集（票 02 的
        互不污染在 05 票状态下继续成立）。"""

        from conftest import make_ep02_units

        roles = CognitiveRoles(
            extractor=StubExtractor(
                script={"ep01": make_units_a14_inconclusive(), "ep02": make_ep02_units()}
            ),
            inference_auditor=StubInferenceAuditor(
                verdicts={"u-002": UnitAuditVerdict(verdict="inconclusive", reason=INCONCLUSIVE_REASON)}
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = tmp_path / "assets"
        rc = run_cli(two_source_corpus, asset_dir, roles, module_name="needs_review_two_source_roles")
        assert rc == 0
        summary = parse_json_block(asset_dir / "run-summary.md")
        statuses = {s["source_id"]: s["status"] for s in summary["sources"]}
        assert statuses == {"ep01": "needs_review", "ep02": "success"}
        trusted_ids = {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]}
        assert trusted_ids == {"u-001", "u-003", "u-101", "u-102", "u-103"}


# ---------------------------------------------------------------------------
# 触界行为（明确不含 / fail loud——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestNeedsReviewBoundaries:
    def test_inconclusive_without_reason_fails_loud(self, tmp_path, ass_file):
        """A14/R4.4 守卫（07 票隔离后的可观察形态）：不确定结论不带可读
        理由（空或纯空白）→ 该 Source 的处理抛错（角色契约破坏；理由
        只能来自替身结论，不容系统兜底措辞），Source failed +
        execution_failure 条目（原因含守卫信息）、退出码 1；守卫不变量
        仍绝对成立——不产出无理由的 needs_review 记录（该单元无任何
        下落）。与 03 票拒绝缺理由守卫对称。"""

        for i, blank_reason in enumerate(("", "   ")):
            roles = CognitiveRoles(
                extractor=StubExtractor(script={"ep01": make_units_with_time_range()[:1]}),
                inference_auditor=StubInferenceAuditor(
                    verdicts={"u-001": UnitAuditVerdict(verdict="inconclusive", reason=blank_reason)}
                ),
                coverage_auditor=StubCoverageAuditor(),
            )
            asset_dir = tmp_path / f"assets-{i}"
            rc = run_cli(
                ass_file, asset_dir, roles, module_name="silent_inconclusive_stub_roles"
            )
            assert rc == 1  # 部分失败（07 票退出码契约）

            src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
            assert src["status"] == "failed"
            assert src["units"] == []  # 无任何单元下落记录（不作兜底处置）
            assert "缺少理由" in src["reason"]

            entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
            assert [(e["category"], e["subject"]) for e in entries] == [
                ("execution_failure", "ep01")
            ]
            assert "缺少理由" in entries[0]["reason"]

    @pytest.mark.parametrize("bad_verdict", ["maybe", "low_confidence"])
    def test_unknown_verdict_fails_loud(self, tmp_path, ass_file, bad_verdict):
        """结论值域守卫（07 票隔离后的可观察形态）：pass/reject/
        inconclusive 之外的结论值（替身契约破坏）→ 该 Source 的处理
        抛错，Source failed + execution_failure 条目（原因含值域外
        结论值），不静默当作任何已知下落处置。含 low_confidence：
        R3.8——"低可信"只是风险信号，不是结论值、更不是实体状态，
        冒充结论值即契约破坏。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_with_time_range()[:1]}),
            inference_auditor=StubInferenceAuditor(
                verdicts={"u-001": UnitAuditVerdict(verdict=bad_verdict, reason="受控：值域外结论")}
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = tmp_path / f"assets-{bad_verdict}"
        rc = run_cli(ass_file, asset_dir, roles, module_name="unknown_verdict_stub_roles")

        assert rc == 1  # 部分失败（07 票退出码契约）
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "failed"
        assert f"{bad_verdict!r}" in src["reason"]

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [e["category"] for e in entries] == ["execution_failure"]
        assert f"{bad_verdict!r}" in entries[0]["reason"]

    def test_inconclusive_takes_precedence_over_missing_reference(self, tmp_path, ass_file):
        """票内裁定（优先序，与 03 票拒绝先例一致）：待复核是完整下落
        （不进发布集 + 摘要留痕），先于无引用门与忠实性程序门生效；
        后两者只守"通过"路径。不确定且无引用的单元不走 06 票无引用门
        （无引用门只处置通过结论的单元）。"""

        no_ref_unit = KnowledgeUnit(
            unit_id="u-noref-inconclusive",
            unit_type="claim",
            statement="基准情形使递归终止",
            source_reference=None,
        )
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": (no_ref_unit,)}),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-noref-inconclusive": UnitAuditVerdict(
                        verdict="inconclusive", reason="受控：无引用单元无法可靠判定"
                    )
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "needs_review"
        assert src["units"][0]["status"] == "needs_review"
        assert src["units"][0]["reason"] == "受控：无引用单元无法可靠判定"


# 06 票前置挡板（test_missing_reference_still_fails_loud）随无引用门
# 落地而退役：无引用单元的下落由 test_missing_reference_disposition.py
# 全面验收（rejected + audit_rejection + Source success）。
