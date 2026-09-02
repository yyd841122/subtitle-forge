"""Ticket 04 验收：忠实性审计的程序比对——假引用拦截（R3.1、A1、Impl 2/5）。

审计门自此 = 程序比对 ∧ 推理审计 双通过：即使推理审计替身判「通过」，
quoted_text 无法在所指 Segment 原文中程序比对成立的单元也不进可信
发布集，并以 audit_rejection 落缺口报告（复用 03 票的拒绝下落机制：
不进发布集 + 缺口条目 + 运行摘要 rejected）。程序门位于发布集准入前、
不经任何认知角色（Impl 5：忠实性审计含纯程序比对部分，不由生成同一
内容的替身自评）。断言只针对外部产物（Testing Decisions）。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

from conftest import (
    SEG_TEXTS,
    make_units_a1_fake_quote,
    make_units_newline_variants,
    parse_json_block,
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

# 忠实性拒绝理由的稳定前缀：缺口条目与运行摘要据此可辨原因来自忠实性
# 程序比对（AC2），区别于推理审计的拒绝理由。
FAITHFULNESS_REASON_PREFIX = "忠实性比对不成立"


def run_cli(
    ass_file: Path,
    asset_dir: Path,
    roles: CognitiveRoles,
    module_name: str = "faithfulness_stub_roles",
) -> int:
    """注册替身模块并执行 CLI，返回退出码。"""

    mod = types.ModuleType(module_name)
    mod.stub_roles = lambda: roles  # type: ignore[attr-defined]
    sys.modules[module_name] = mod
    from subtitle_forge.cli import main

    return main(["run", str(ass_file.parent), str(asset_dir), "--stub-module", module_name])


def run_and_write(tmp_path: Path, ass_file: Path, roles: CognitiveRoles) -> Path:
    """走 CLI 端到端（含落盘），返回资产目录。"""

    tmp_path.mkdir(parents=True, exist_ok=True)
    asset_dir = tmp_path / "assets"
    rc = run_cli(ass_file, asset_dir, roles)
    assert rc == 0, "含忠实性被拒单元的运行应成功（A4：全部单元有明确下落即成功）"
    return asset_dir


def pass_all_roles(script: dict) -> CognitiveRoles:
    """推理审计全 pass 的认知角色集——被拒只可能来自程序门（受控前提）。"""

    return CognitiveRoles(
        extractor=StubExtractor(script=script),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


def single_unit(unit: KnowledgeUnit) -> dict:
    return {"ep01": (unit,)}


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestFaithfulnessAcceptance:
    def test_fake_quote_rejected_despite_inference_pass(self, tmp_path, ass_file):
        """AC1：假引用单元 + 推理审计替身 pass → 该单元不在可信发布集
        （审计门 = 程序比对 ∧ 推理审计，双通过缺一不可）。"""

        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles({"ep01": make_units_a1_fake_quote()}))
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-001", "u-003"}

    def test_gap_report_identifies_faithfulness_cause(self, tmp_path, ass_file):
        """AC2：缺口报告 audit_rejection 条目可辨原因来自忠实性比对——
        category=audit_rejection、指向单元、reason 以稳定前缀开头、
        下落与审计拒绝一致（复用 03 票机制）。"""

        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles({"ep01": make_units_a1_fake_quote()}))
        report = parse_json_block(asset_dir / "gap-report.md")
        assert len(report["entries"]) == 1
        entry = report["entries"][0]
        assert entry["category"] == "audit_rejection"
        assert entry["source_id"] == "ep01"
        assert entry["subject"] == "u-002"
        assert entry["reason"].startswith(FAITHFULNESS_REASON_PREFIX)
        assert entry["outcome"] == "不进入发布集，记录在案"

    def test_real_quote_units_unaffected_same_run(self, tmp_path, ass_file):
        """AC3：同 run 中真引用单元照常通过（比对不误伤）——发布集含
        u-001/u-003；运行摘要 u-002 rejected（理由可辨忠实性来源）、
        其余 passed；Source 仍 success（A4）。"""

        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles({"ep01": make_units_a1_fake_quote()}))
        summary = parse_json_block(asset_dir / "run-summary.md")

        src = summary["sources"][0]
        assert src["source_id"] == "ep01"
        assert src["status"] == "success"
        unit_records = {u["unit_id"]: u for u in src["units"]}
        assert {uid: u["status"] for uid, u in unit_records.items()} == {
            "u-001": "passed",
            "u-002": "rejected",
            "u-003": "passed",
        }
        assert unit_records["u-002"]["reason"].startswith(FAITHFULNESS_REASON_PREFIX)
        assert unit_records["u-001"]["reason"] == ""


# ---------------------------------------------------------------------------
# 票内裁定：初始算法（Open Impl 10）与比对基准（所指 Segment.text）
# ---------------------------------------------------------------------------


class TestFaithfulnessGateBehavior:
    def test_minimal_normalization_tolerates_layout_only_difference(
        self, tmp_path, newline_ass_file
    ):
        """票内裁定（初始算法 = 最小规范化后匹配）：引用与原文只差排版
        空白（换行 \\N vs 空格）时比对成立，不误伤；同样排版之下改动
        一个非空白字符（两→三）则拒绝——只容忍排版、不容忍内容改动。"""

        asset_dir = run_and_write(
            tmp_path, newline_ass_file, pass_all_roles({"ep01": make_units_newline_variants()})
        )
        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == {"u-nl-space"}

        report = parse_json_block(asset_dir / "gap-report.md")
        assert [e["subject"] for e in report["entries"]] == ["u-nl-alter"]
        assert report["entries"][0]["reason"].startswith(FAITHFULNESS_REASON_PREFIX)

    def test_partial_substring_quote_passes(self, tmp_path, ass_file):
        """引用文本可以是指片段的子串（不必整段逐字复述）——比对语义是
        "存在于原文"，不是"等于原文"；部分引用同样成立。"""

        partial = KnowledgeUnit(
            unit_id="u-partial",
            unit_type="claim",
            statement="递归函数会调用自身",
            source_reference=SourceReference(
                segment_id=seg_id(1),
                quoted_text="函数调用自身并逐步缩小问题规模",
                locator=TimeRangeLocator(start_ms=2000, end_ms=5000),
            ),
        )
        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles(single_unit(partial)))

        assert {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]} == {
            "u-partial"
        }
        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []

    def test_whitespace_run_collapse_tolerated(self, tmp_path, ass_file):
        """空白连续段折叠为单个空格：引用把原文的单个空格写成两个空格
        （排版差异）仍比对成立——但这是排版容忍的上限。"""

        double_space_quote = SEG_TEXTS[1].replace("基准情形 n", "基准情形  n")
        assert double_space_quote != SEG_TEXTS[1]  # 受控前提：确实引入了排版差异
        unit = KnowledgeUnit(
            unit_id="u-ws-run",
            unit_type="method",
            statement="求阶乘：先写基准情形 n=0 返回 1，再递归调用自身",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=double_space_quote,
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        )
        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles(single_unit(unit)))

        assert {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]} == {
            "u-ws-run"
        }

    def test_meaningful_space_deletion_rejected(self, tmp_path, ass_file):
        """空白数量的减少不是排版差异：删去有意义的单个空格
        （"n 等于零"→"n等于零"）后引用与原文不再逐字对应——仍拒绝。
        空白折叠不容忍空白的消失，只容忍连续段的等价展开。"""

        no_space_quote = SEG_TEXTS[1].replace(" ", "")
        unit = KnowledgeUnit(
            unit_id="u-ws-gone",
            unit_type="method",
            statement="求阶乘：先写基准情形 n=0 返回 1，再递归调用自身",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=no_space_quote,
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        )
        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles(single_unit(unit)))

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entry = parse_json_block(asset_dir / "gap-report.md")["entries"][0]
        assert entry["subject"] == "u-ws-gone"
        assert entry["reason"].startswith(FAITHFULNESS_REASON_PREFIX)

    def test_comparison_anchored_to_referenced_segment(self, tmp_path, ass_file):
        """比对基准是所指 Segment 的原文（票 anchor）：引用文本真实存在
        于另一片段（seg1）但不存在于所指片段（seg2）→ 仍拒绝——
        quoted_text 与 segment_id 必须对同一片段一致成立。"""

        wrong_anchor = KnowledgeUnit(
            unit_id="u-wrong-seg",
            unit_type="claim",
            statement="递归的核心结构是函数调用自身并逐步缩小问题规模",
            source_reference=SourceReference(
                segment_id=seg_id(2),
                quoted_text=SEG_TEXTS[0],
                locator=TimeRangeLocator(start_ms=7500, end_ms=13200),
            ),
        )
        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles(single_unit(wrong_anchor)))

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entry = parse_json_block(asset_dir / "gap-report.md")["entries"][0]
        assert entry["subject"] == "u-wrong-seg"
        assert entry["reason"].startswith(FAITHFULNESS_REASON_PREFIX)

    def test_dangling_segment_reference_rejected(self, tmp_path, ass_file):
        """所指片段不存在于该 Source → 引用无法在原文中比对成立 → 按忠实
        性拒绝落缺口（指向的锚点本身无效，与引用文本真假同等不成立）。"""

        dangling = KnowledgeUnit(
            unit_id="u-dangling",
            unit_type="claim",
            statement="递归的核心结构是函数调用自身并逐步缩小问题规模",
            source_reference=SourceReference(
                segment_id="ep01#seg9999",
                quoted_text=SEG_TEXTS[0],
                locator=TimeRangeLocator(start_ms=1000, end_ms=6000),
            ),
        )
        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles(single_unit(dangling)))

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entry = parse_json_block(asset_dir / "gap-report.md")["entries"][0]
        assert entry["subject"] == "u-dangling"
        assert entry["reason"].startswith(FAITHFULNESS_REASON_PREFIX)

    def test_empty_quoted_text_rejected(self, tmp_path, ass_file):
        """空引用文本不构成逐字引用：空串是任意文本的子串，不得因此
        空洞成立而放行——按忠实性拒绝。"""

        empty_quote = KnowledgeUnit(
            unit_id="u-empty-quote",
            unit_type="claim",
            statement="递归的核心结构是函数调用自身并逐步缩小问题规模",
            source_reference=SourceReference(
                segment_id=seg_id(1),
                quoted_text="",
                locator=TimeRangeLocator(start_ms=1000, end_ms=6000),
            ),
        )
        asset_dir = run_and_write(tmp_path, ass_file, pass_all_roles(single_unit(empty_quote)))

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entry = parse_json_block(asset_dir / "gap-report.md")["entries"][0]
        assert entry["subject"] == "u-empty-quote"
        assert entry["reason"].startswith(FAITHFULNESS_REASON_PREFIX)


# ---------------------------------------------------------------------------
# 触界行为（明确不含，fail loud——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestFaithfulnessBoundaries:
    def test_reasoning_reject_keeps_single_disposition(self, tmp_path, ass_file):
        """票内裁定（单单元单条下落）：本票程序门按 What 措辞只作用于
        "即使推理审计替身判「通过」"的准入路径；推理审计已拒的单元已有
        完整下落（03 票裁定：拒绝先于后续挡板/程序门生效），不再经忠实
        性比对留第二条缺口——单单元单条目，reason 来自推理审计，对账
        （A3）中一个单元恰有一个状态与一条下落。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_a1_fake_quote()}),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-002": UnitAuditVerdict(verdict="reject", reason="受控：推理审计拒绝假引用单元")
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]} == {
            "u-001",
            "u-003",
        }
        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert len(entries) == 1
        assert entries[0]["subject"] == "u-002"
        assert entries[0]["reason"] == "受控：推理审计拒绝假引用单元"

    def test_inconclusive_keeps_single_disposition(self, tmp_path, ass_file):
        """票内裁定（单单元单条下落，05 票语义落地后）：假引用 + 不确定
        结论 → 待复核下落（运行摘要 needs_review），不经忠实性比对留
        拒绝条目——程序门只守"通过"路径；一个单元恰有一个状态与一条
        下落（对账 A3），拒绝与待复核不混用（R4.6）。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_a1_fake_quote()[:2]}),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-002": UnitAuditVerdict(verdict="inconclusive", reason="受控：无法可靠判定")
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]} == {
            "u-001"
        }
        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []
        src = parse_json_block(asset_dir / "run-summary.md")["sources"][0]
        unit_records = {u["unit_id"]: u for u in src["units"]}
        assert unit_records["u-002"]["status"] == "needs_review"
        assert unit_records["u-002"]["reason"] == "受控：无法可靠判定"

    def test_missing_reference_not_intercepted_by_faithfulness_gate(self, tmp_path, ass_file):
        """触界（06 票无引用门落地后的 04 界线）：无引用单元没有可比对
        的 quoted_text，不属忠实性比对场景——其拒绝理由是 06 票的
        「无来源引用」前缀，不是「忠实性比对不成立」；程序门不得拦截
        或前置处置该路径。"""

        no_ref_unit = KnowledgeUnit(
            unit_id="u-noref",
            unit_type="claim",
            statement="基准情形使递归终止",
            source_reference=None,
        )
        roles = pass_all_roles(single_unit(no_ref_unit))
        asset_dir = run_and_write(tmp_path, ass_file, roles)

        assert parse_json_block(asset_dir / "trusted-set.md")["entries"] == []
        entry = parse_json_block(asset_dir / "gap-report.md")["entries"][0]
        assert entry["subject"] == "u-noref"
        assert entry["reason"].startswith("无来源引用")
        assert not entry["reason"].startswith(FAITHFULNESS_REASON_PREFIX)
