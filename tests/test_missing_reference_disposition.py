"""Ticket 06 验收：无 Source Reference 单元的下落（R2.4、A17）。

A17 场景：提炼替身产出无引用单元（其余正常），推理审计替身全 pass
（受控前提：该单元只可能被无引用门处置）。票内裁定（见票面裁定记录）：
实体状态 rejected、Gap Category audit_rejection——无引用单元的提炼与
审查流程完整走完，缺陷在准入凭据（R2.4：Source Reference = 引用文本 +
定位）而非执行，故属准入性拒绝（与 04 票程序门同族，Spec Impl 2 /
ADR-0003），不属 execution_failure；经 03 票统一下落机制留痕，reason 以
稳定前缀「无来源引用」开头（三类拒绝来源在外部产物中可辨）；含此类
单元的 Source 仍 success（A4：已决下落不妨碍成功，也不触发
needs_review——rejected 是已决结论非未决问题）。断言只针对外部产物
（Testing Decisions）。
"""

from __future__ import annotations

from pathlib import Path

from conftest import (
    SEG_TEXTS,
    make_ep02_units,
    make_units_a17_no_reference,
    parse_json_block,
    run_cli_with_roles,
    seg_id,
)

from subtitle_forge.model import KnowledgeUnit, SourceReference, TimeRangeLocator
from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
    UnitAuditVerdict,
)

# 无引用拒绝理由的稳定前缀（票内裁定）：缺口条目与运行摘要据此可辨
# 原因来自 R2.4 无引用门，区别于推理审计拒绝与忠实性程序比对拒绝。
MISSING_REFERENCE_REASON_PREFIX = "无来源引用"


def run_cli(
    ass_file_or_dir: Path,
    asset_dir: Path,
    roles: CognitiveRoles,
    module_name: str = "missing_reference_stub_roles",
) -> int:
    """注册替身模块并执行 CLI，返回退出码（共享通道，见 conftest）。"""

    return run_cli_with_roles(ass_file_or_dir, asset_dir, roles, module_name)


def run_and_write(tmp_path: Path, ass_file: Path, roles: CognitiveRoles) -> Path:
    """走 CLI 端到端（含落盘），返回资产目录。"""

    tmp_path.mkdir(parents=True, exist_ok=True)
    asset_dir = tmp_path / "assets"
    rc = run_cli(ass_file, asset_dir, roles)
    # 无引用单元是实体下落不是运行失败（R4.6：Source 失败 = 流程无法
    # 完整完成；含已决下落单元的运行完整结束），运行应成功。
    assert rc == 0, "含无引用单元的运行应成功（rejected 是实体状态，非运行失败）"
    return asset_dir


def no_reference_roles() -> CognitiveRoles:
    """A17 场景的认知角色集：提炼脚本产出含无引用单元的候选集，推理
    审计替身全 pass（默认）——无引用单元只可能被无引用门处置。"""

    return CognitiveRoles(
        extractor=StubExtractor(script={"ep01": make_units_a17_no_reference()}),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestMissingReferenceAcceptance:
    def test_no_reference_unit_absent_from_trusted_set(self, tmp_path, ass_file):
        """AC1：A17 fixture（替身产出无引用单元，其余正常）→ 该单元不出
        现在可信发布集，其余单元照常进入。"""

        asset_dir = run_and_write(tmp_path, ass_file, no_reference_roles())
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-001", "u-003"}

    def test_run_summary_records_missing_reference(self, tmp_path, ass_file):
        """AC2：运行摘要有该单元的记录——状态可辨（票内裁定 rejected）、
        reason 提「无来源引用」（非空、以稳定前缀开头，区别于其他拒绝
        来源）。"""

        asset_dir = run_and_write(tmp_path, ass_file, no_reference_roles())
        summary = parse_json_block(asset_dir / "run-summary.md")
        unit_records = {u["unit_id"]: u for u in summary["sources"][0]["units"]}
        assert unit_records["u-002"]["status"] == "rejected"
        reason = unit_records["u-002"]["reason"]
        assert reason  # 非空
        assert reason.startswith(MISSING_REFERENCE_REASON_PREFIX)

    def test_gap_report_entry_and_source_success(self, tmp_path, ass_file):
        """AC3：缺口报告有指向该单元的条目（票内裁定 audit_rejection，
        含 Source / 指向单元 / 原因 / 下落——A11）；Source 最终状态与
        A4 语义一致——单元有（已决）下落即不妨碍 success，也不触发
        needs_review。"""

        asset_dir = run_and_write(tmp_path, ass_file, no_reference_roles())
        report = parse_json_block(asset_dir / "gap-report.md")
        assert len(report["entries"]) == 1
        entry = report["entries"][0]
        assert entry["category"] == "audit_rejection"
        assert entry["source_id"] == "ep01"
        assert entry["subject"] == "u-002"
        assert entry["reason"].startswith(MISSING_REFERENCE_REASON_PREFIX)
        assert entry["outcome"] == "不进入发布集，记录在案"

        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "success"


# ---------------------------------------------------------------------------
# 行为语义（票内裁定与 Spec 条款的可观察化）
# ---------------------------------------------------------------------------


class TestMissingReferenceBehavior:
    def test_no_reference_unit_stays_in_faithful_layer_with_null_reference(
        self, tmp_path, ass_file
    ):
        """无引用单元仍是提炼产物，留在忠实层资产（R2.5：审查结果不改
        忠实层；无引用门只决定发布集成员资格）；其 source_reference 以
        null 形态如实落盘（忠实层忠实记录提炼产出，不替它补引用）。
        资产路径从运行摘要的 asset_organization 自描述清单读取。"""

        asset_dir = run_and_write(tmp_path, ass_file, no_reference_roles())
        org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]
        units_doc = parse_json_block(asset_dir / org["faithful_layer"]["per_source"][0])
        units_by_id = {u["unit_id"]: u for u in units_doc["units"]}
        assert set(units_by_id) == {"u-001", "u-002", "u-003"}
        assert units_by_id["u-002"]["source_reference"] is None

    def test_rejection_sources_distinguishable_in_artifacts(self, tmp_path, ass_file):
        """三类拒绝来源在外部产物中可辨（票内裁定：reason 稳定前缀）：
        同一 Source 内——推理审计拒绝（替身理由）、忠实性程序门拒绝
        （「忠实性比对不成立」前缀）、无引用门拒绝（「无来源引用」前缀）
        ——各单元一条下落，三个前缀互不混淆。"""

        fake_quote_unit = KnowledgeUnit(
            unit_id="u-fake",
            unit_type="claim",
            statement="基准情形在 n 等于一返回一",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text="任何递归函数的基准情形都在 n 等于一时返回一",
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        )
        no_ref_unit = KnowledgeUnit(
            unit_id="u-noref",
            unit_type="method",
            statement="求阶乘：先写基准情形，再递归调用自身",
            source_reference=None,
        )
        overreach_unit = KnowledgeUnit(
            unit_id="u-overreach",
            unit_type="claim",
            statement="一切递归函数的基准情形都是 n 等于零时返回一",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=SEG_TEXTS[1],
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        )
        roles = CognitiveRoles(
            extractor=StubExtractor(
                script={"ep01": (fake_quote_unit, no_ref_unit, overreach_unit)}
            ),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-overreach": UnitAuditVerdict(
                        verdict="reject", reason="受控：断言超出引用支持范围"
                    )
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert len(entries) == 3  # 单单元单条下落（A3 对账前提）
        reasons = {e["subject"]: e["reason"] for e in entries}
        assert reasons["u-fake"].startswith("忠实性比对不成立")
        assert reasons["u-noref"].startswith(MISSING_REFERENCE_REASON_PREFIX)
        assert reasons["u-overreach"] == "受控：断言超出引用支持范围"

        raw_units = parse_json_block(asset_dir / "run-summary.md")["sources"][0]["units"]
        # 对账：每个提炼产出的单元在运行摘要中恰有一条记录（先断言列表
        # 基数与 unit_id 唯一，再转字典——重复下落与静默消失都过不了
        # 这关，R4.3；转字典本身会掩盖重复记录）。
        assert len(raw_units) == 3
        assert len({u["unit_id"] for u in raw_units}) == len(raw_units)
        assert {u["unit_id"] for u in raw_units} == {"u-fake", "u-noref", "u-overreach"}
        units = {u["unit_id"]: u for u in raw_units}
        assert {uid: u["status"] for uid, u in units.items()} == {
            "u-fake": "rejected",
            "u-noref": "rejected",
            "u-overreach": "rejected",
        }
        # 对账：每个提炼产出的单元在运行摘要中恰有一条记录，无静默消失（R4.3）。
        assert len(units) == 3

    def test_all_units_no_reference_source_still_success(self, tmp_path, ass_file):
        """边界对照（与 03 票「整源被拒仍 success」并排）：Source 内全部
        单元无引用 → 发布集为空、缺口条目逐单元留痕、Source 仍 success
        ——已决下落（哪怕是准入凭据缺失）不妨碍成功（A4），与「存在
        未决问题 ⇒ needs_review」形成语义对照。"""

        units = tuple(
            KnowledgeUnit(
                unit_id=f"u-noref-{i}",
                unit_type="claim",
                statement=statement,
                source_reference=None,
            )
            for i, statement in enumerate(
                ("递归的核心结构是函数调用自身", "递归深度必须有限", "基准情形使递归终止")
            )
        )
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": units}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert {e["subject"] for e in entries} == {"u-noref-0", "u-noref-1", "u-noref-2"}
        assert all(e["category"] == "audit_rejection" for e in entries)
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        assert src["status"] == "success"
        assert all(u["status"] == "rejected" for u in src["units"])

    def test_second_source_unaffected_by_no_reference(self, tmp_path, two_source_corpus):
        """跨 Source 隔离：ep01 含无引用单元、ep02 全正常 → ep02 照常
        success 且其单元照常进发布集；ep01 因已决拒绝下落仍 success
        （不因 ep01 的问题牵连 ep02 的准入，票 02 互不污染继续成立）。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(
                script={"ep01": make_units_a17_no_reference(), "ep02": make_ep02_units()}
            ),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = tmp_path / "assets"
        rc = run_cli(two_source_corpus, asset_dir, roles, module_name="no_ref_two_source_roles")
        assert rc == 0

        summary = parse_json_block(asset_dir / "run-summary.md")
        statuses = {s["source_id"]: s["status"] for s in summary["sources"]}
        assert statuses == {"ep01": "success", "ep02": "success"}
        trusted_ids = {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]}
        assert trusted_ids == {"u-001", "u-003", "u-101", "u-102", "u-103"}
        gap_subjects = {e["subject"] for e in parse_json_block(asset_dir / "gap-report.md")["entries"]}
        assert gap_subjects == {"u-002"}


# ---------------------------------------------------------------------------
# 触界行为（明确不含——不得提前实现后续能力或弱化已有边界）
# ---------------------------------------------------------------------------


class TestMissingReferenceBoundaries:
    def test_reference_defects_stay_with_faithfulness_gate(self, tmp_path, ass_file):
        """明确不含（引用有效性分级体系不建）：无引用门只处置
        source_reference 为 None 的单元——「有引用但引用缺陷」（如
        segment_id 不存在）仍由 04 票忠实性程序门以其自己的理由处置，
        不得归并进「无来源引用」下落（两类下落 reason 前缀可辨）。"""

        bad_segment_unit = KnowledgeUnit(
            unit_id="u-bad-seg",
            unit_type="claim",
            statement="递归深度必须有限，否则栈会溢出",
            source_reference=SourceReference(
                segment_id="ep01#seg9999",  # 不存在于该 Source
                quoted_text=SEG_TEXTS[2],
                locator=TimeRangeLocator(start_ms=14000, end_ms=18300),
            ),
        )
        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": (bad_segment_unit,)}),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entry = parse_json_block(asset_dir / "gap-report.md")["entries"][0]
        assert entry["category"] == "audit_rejection"
        assert entry["subject"] == "u-bad-seg"
        assert entry["reason"].startswith("忠实性比对不成立")
        assert not entry["reason"].startswith(MISSING_REFERENCE_REASON_PREFIX)

    def test_pass_verdict_no_reference_no_longer_fails_loud(self, tmp_path, ass_file):
        """挡板退役：01–05 票在通过路径上的 missing_source_reference
        fail-loud 挡板由本票的下落语义取代——通过结论 + 无引用单元不再
        抛错，运行完整结束并产出全部三类外部产物（该单元 rejected）。"""

        asset_dir = run_and_write(tmp_path, ass_file, no_reference_roles())
        # 运行成功（run_and_write 已断言 rc == 0）且三类产物结构完整：
        assert parse_json_block(asset_dir / "trusted-set.md")["entries"]
        assert parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert parse_json_block(asset_dir / "run-summary.md")["sources"]
