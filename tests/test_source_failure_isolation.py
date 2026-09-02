"""Ticket 07 验收：Source 失败隔离与继续批处理（R4.6、R4.2、R5.5、A3、A11）。

某 Source 的处理抛错（替身脚本注入）→ 该 Source ``failed``、缺口报告
``execution_failure`` 条目（含原因）、其余 Source 照常完成、运行结束可辨
部分失败（退出码 1 + stdout 列名失败 Source）；全局性错误（AC 钉死的
fixture：资产目录不可写）仍中止整批（退出码 3，无半成品全局产物）。

票内裁定（见票面记录）：Source 局部错误 = 单个 Source 处理作用域内抛出
的一切 Exception（含 03/05 票守卫）；全局错误初始清单 = Corpus 装载
失败/空 Corpus、替身模块装载失败、资产落盘失败。失败 Source 的原子性：
无单元记录、无忠实层资产、任何单元不进发布集（半成品整体作废）。
退出码契约：0 无 failed / 1 部分 failed / 2 用法 / 3 全局中止。
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

from conftest import (
    make_ep02_units,
    make_ep03_units,
    make_units_with_time_range,
    parse_json_block,
    run_cli_with_roles,
)

from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
    UnitAuditVerdict,
)

EP01_UNITS = {"u-001", "u-002", "u-003"}
EP02_UNITS = {"u-101", "u-102", "u-103"}
EP03_UNITS = {"u-201", "u-202", "u-203"}

# chmod 权限挡板对 root 无效（root 可写任意目录）——以 root 跑测试时
# 跳过依赖权限的 fixture，避免误报。
_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


def isolated_roles() -> CognitiveRoles:
    """07 验收的受控角色集：提炼脚本只含 ep01/ep03——ep02 被调用即抛错
    （替身脚本注入的失败种子，AC1 形态），ep01/ep03 照常产出全部单元。"""

    return CognitiveRoles(
        extractor=StubExtractor(
            script={"ep01": make_units_with_time_range(), "ep03": make_ep03_units()},
        ),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


def all_scripted_roles() -> CognitiveRoles:
    """三 Source 全部正常脚本化的对照角色集（全局错误场景用：处理本身
    健康，失败由资产目录触发）。"""

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


def run_and_write(corpus_dir: Path, tmp_path: Path, roles: CognitiveRoles) -> tuple[int, Path]:
    """三 Source Corpus 端到端（含落盘），返回（退出码, 资产目录）。"""

    asset_dir = tmp_path / "assets"
    rc = run_cli_with_roles(corpus_dir, asset_dir, roles, "failure_isolation_stub_roles")
    return rc, asset_dir


def faithful_source_ids(asset_dir: Path) -> set[str]:
    """从运行摘要的 asset_organization 自描述清单读出已写忠实层资产的
    Source 集合（不硬编码路径）。"""

    org = parse_json_block(asset_dir / "run-summary.md")["asset_organization"]
    return {
        parse_json_block(asset_dir / rel)["source_id"]
        for rel in org["faithful_layer"]["per_source"]
    }


# ---------------------------------------------------------------------------
# 验收断言（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestFailureIsolationAcceptance:
    def test_second_source_extraction_failure_isolated(self, three_source_corpus, tmp_path):
        """AC1：三 Source、第二个（ep02）提炼替身抛错 → ep01/ep03 正常
        产出且发布集含其全部单元（互不污染）；ep02 failed + gap
        execution_failure 条目（含原因——替身抛错信息可辨，A11）。"""

        rc, asset_dir = run_and_write(three_source_corpus, tmp_path, isolated_roles())
        assert rc == 1

        trusted = parse_json_block(asset_dir / "trusted-set.md")
        assert {e["unit_id"] for e in trusted["entries"]} == EP01_UNITS | EP03_UNITS
        assert all(e["source_id"] != "ep02" for e in trusted["entries"])

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["category"] == "execution_failure"
        assert entry["source_id"] == "ep02"
        assert entry["subject"] == "ep02"
        assert "不在预设脚本中" in entry["reason"]  # 原因含真实错误信息（可辨）
        assert entry["outcome"].strip()  # 下落非空（A11）

    def test_exit_code_and_output_distinguish_partial_failure(
        self, three_source_corpus, tmp_path, capsys
    ):
        """AC2：部分失败退出码 = 1（票内裁定），stdout 明确「部分失败」
        并列出失败 Source id（输出可辨部分失败）。"""

        rc, _ = run_and_write(three_source_corpus, tmp_path, isolated_roles())
        assert rc == 1
        out = capsys.readouterr().out
        assert "部分失败" in out
        assert "ep02" in out

    def test_every_source_has_status_no_silent_disappearance(
        self, three_source_corpus, tmp_path
    ):
        """AC2：全部 Source 均有实体状态（A3 无静默消失）——三个 Source
        全部在运行摘要中，ep02 failed 且 reason 非空。"""

        _, asset_dir = run_and_write(three_source_corpus, tmp_path, isolated_roles())
        summary = parse_json_block(asset_dir / "run-summary.md")
        statuses = {s["source_id"]: s["status"] for s in summary["sources"]}
        assert statuses == {"ep01": "success", "ep02": "failed", "ep03": "success"}

        failed = next(s for s in summary["sources"] if s["source_id"] == "ep02")
        assert failed["reason"].strip()

    @pytest.mark.skipif(_ROOT, reason="root 不受目录权限挡板约束")
    def test_global_error_unwritable_asset_dir_aborts_clean(
        self, three_source_corpus, tmp_path, capsys
    ):
        """AC3：全局错误 fixture（资产目录不可写）→ 明确中止：退出码 3
        （票内裁定：全局中止族）、stderr 可辨全局错误，无半成品产物
        （三个全局产物与忠实层/审查层/衍生层目录均未写出——落盘在
        首个写动作即抛错，R5.5）。"""

        asset_dir = tmp_path / "assets"
        asset_dir.mkdir()
        asset_dir.chmod(0o500)  # r-x：目录存在但不可写（无子目录可创建）
        try:
            rc = run_cli_with_roles(
                three_source_corpus, asset_dir, all_scripted_roles(), "global_unwritable_roles"
            )
        finally:
            asset_dir.chmod(0o700)

        assert rc == 3
        err = capsys.readouterr().err
        assert "全局错误" in err and "中止" in err
        for name in (
            "trusted-set.md",
            "gap-report.md",
            "run-summary.md",
            "sources",
            "review",
            "derived",
        ):
            assert not (asset_dir / name).exists(), f"全局中止不得留下半成品产物：{name}"


# ---------------------------------------------------------------------------
# 行为语义（票内裁定与 Spec 条款的可观察化）
# ---------------------------------------------------------------------------


class _AuditorExplodingOnU102(StubInferenceAuditor):
    """推理审计替身：u-101 照常给结论（通过），u-102 被调用即抛错——
    单元级审查中途失败的受控种子（原子性裁定的触发器）。"""

    def audit_unit(self, source, unit):
        if unit.unit_id == "u-102":
            raise RuntimeError("受控：推理审计环节异常")
        return super().audit_unit(source, unit)


class _CoverageExplodingOnEp02(StubCoverageAuditor):
    """覆盖审计替身：ep02 被调用即抛错——Source 处理最晚环节失败的
    受控种子（隔离边界覆盖整个处理作用域的证明）。"""

    def audit_coverage(self, source, units):
        if source.source_id == "ep02":
            raise RuntimeError("受控：覆盖审计环节异常")
        return super().audit_coverage(source, units)


class _ExtractorInterruptOnEp02(StubExtractor):
    """提炼替身：ep02 被调用即发 KeyboardInterrupt——BaseException
    非隔离边界（人为中断必须中止整批，不得被吞成 Source 失败）。"""

    def extract(self, source):
        if source.source_id == "ep02":
            raise KeyboardInterrupt("受控：人为中断")
        return super().extract(source)


class TestFailureIsolationBehavior:
    def test_mid_processing_failure_discards_partial_state(
        self, three_source_corpus, tmp_path
    ):
        """原子性（票内裁定）：提炼完成、单元审查中途抛错 → 该 Source
        失败发生前已通过审查的单元（u-101）也不进发布集、不留单元记录
        （R4.6：无法形成符合规格要求的 Source 结果，半成品整体作废）；
        execution_failure 条目是其唯一留痕，前后 Source 照常完成。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(
                script={
                    "ep01": make_units_with_time_range(),
                    "ep02": make_ep02_units(),
                    "ep03": make_ep03_units(),
                }
            ),
            inference_auditor=_AuditorExplodingOnU102(),
            coverage_auditor=StubCoverageAuditor(),
        )
        rc, asset_dir = run_and_write(three_source_corpus, tmp_path, roles)
        assert rc == 1

        # u-101 在异常发生前已通过——半成品作废，不得泄入发布集
        trusted_ids = {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]}
        assert trusted_ids == EP01_UNITS | EP03_UNITS

        summary = parse_json_block(asset_dir / "run-summary.md")
        ep02 = next(s for s in summary["sources"] if s["source_id"] == "ep02")
        assert ep02["status"] == "failed"
        assert ep02["units"] == []  # 无任何单元下落记录（不是部分下落）

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert len(entries) == 1
        assert entries[0]["category"] == "execution_failure"
        assert "受控：推理审计环节异常" in entries[0]["reason"]

    def test_failed_source_has_no_faithful_asset(self, three_source_corpus, tmp_path):
        """报告形态（票内裁定）：失败 Source 不写忠实层资产——为失败
        Source 写空资产会与「提炼完成但产出为空」（08 票保守提炼场景）
        不可辨；其下落由运行摘要（failed + reason）与缺口报告显性承载。
        asset_organization 的 per_source 清单只含完成的 Source。"""

        _, asset_dir = run_and_write(three_source_corpus, tmp_path, isolated_roles())
        assert faithful_source_ids(asset_dir) == {"ep01", "ep03"}

    def test_coverage_stage_failure_isolated(self, three_source_corpus, tmp_path):
        """隔离边界覆盖整个处理作用域（票内裁定）：最晚环节（覆盖审计）
        抛错同样隔离——ep02 单元级下落已全部处置完毕，仍整体作废（无
        发布集条目、无单元记录），ep01/ep03 照常完成。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(
                script={
                    "ep01": make_units_with_time_range(),
                    "ep02": make_ep02_units(),
                    "ep03": make_ep03_units(),
                }
            ),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=_CoverageExplodingOnEp02(),
        )
        rc, asset_dir = run_and_write(three_source_corpus, tmp_path, roles)
        assert rc == 1

        trusted_ids = {
            e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]
        }
        assert trusted_ids == EP01_UNITS | EP03_UNITS

        summary = parse_json_block(asset_dir / "run-summary.md")
        statuses = {s["source_id"]: s["status"] for s in summary["sources"]}
        assert statuses == {"ep01": "success", "ep02": "failed", "ep03": "success"}
        ep02 = next(s for s in summary["sources"] if s["source_id"] == "ep02")
        assert ep02["units"] == []

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [(e["category"], e["subject"]) for e in entries] == [
            ("execution_failure", "ep02")
        ]
        assert "覆盖审计环节异常" in entries[0]["reason"]

    def test_stale_faithful_asset_of_failed_source_removed(self, three_source_corpus, tmp_path):
        """同目录复用（审计修复回归）：先前成功运行写下的失败 Source
        忠实层资产，在本次运行该 Source 失败时被移除——运行摘要的
        asset_organization 按目录现状生成，旧文件会把 failed Source
        误宣告为已产出（失败被误认为已完成，R5.4 精神）。资产路径从
        首次运行的自描述清单读取，不硬编码。"""

        # 首次运行：三 Source 全部成功 → ep02 忠实层资产在位
        rc, asset_dir = run_and_write(three_source_corpus, tmp_path, all_scripted_roles())
        assert rc == 0
        ep02_rel = next(
            rel
            for rel in parse_json_block(asset_dir / "run-summary.md")["asset_organization"][
                "faithful_layer"
            ]["per_source"]
            if parse_json_block(asset_dir / rel)["source_id"] == "ep02"
        )
        assert (asset_dir / ep02_rel).exists()

        # 二次运行（同目录）：ep02 失败 → 旧忠实层资产移除
        rc, asset_dir = run_and_write(three_source_corpus, tmp_path, isolated_roles())
        assert rc == 1
        assert faithful_source_ids(asset_dir) == {"ep01", "ep03"}
        assert not (asset_dir / ep02_rel).exists()

    def test_role_contract_guard_isolated_to_source(self, two_source_corpus, tmp_path):
        """Open Impl 13 初始判据（票内裁定）：03/05 票守卫（角色契约破坏，
        如拒绝结论缺理由）的异常属 Source 局部错误——只使该 Source
        failed，另一 Source 照常完成；守卫不变量仍成立（不产出缺原因的
        拒绝条目——该单元无任何下落，execution_failure 是唯一留痕）。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(
                script={"ep01": make_units_with_time_range()[:1], "ep02": make_ep02_units()}
            ),
            inference_auditor=StubInferenceAuditor(
                verdicts={"u-001": UnitAuditVerdict(verdict="reject", reason="   ")}
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = tmp_path / "assets"
        rc = run_cli_with_roles(two_source_corpus, asset_dir, roles, "guard_isolation_roles")

        assert rc == 1
        summary = parse_json_block(asset_dir / "run-summary.md")
        statuses = {s["source_id"]: s["status"] for s in summary["sources"]}
        assert statuses == {"ep01": "failed", "ep02": "success"}
        assert "缺少理由" in next(s for s in summary["sources"] if s["source_id"] == "ep01")["reason"]

        trusted_ids = {e["unit_id"] for e in parse_json_block(asset_dir / "trusted-set.md")["entries"]}
        assert trusted_ids == EP02_UNITS

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [(e["category"], e["source_id"]) for e in entries] == [
            ("execution_failure", "ep01")
        ]
        assert "缺少理由" in entries[0]["reason"]

    def test_needs_review_run_is_not_partial_failure(self, ass_file, tmp_path):
        """退出码契约（票内裁定）：needs_review 是已完成的实体状态而非
        运行失败（R4.6 三态不混用）——只含待复核 Source 的运行退出码 0。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={"ep01": make_units_with_time_range()[:1]}),
            inference_auditor=StubInferenceAuditor(
                verdicts={
                    "u-001": UnitAuditVerdict(verdict="inconclusive", reason="受控：无法可靠判定")
                }
            ),
            coverage_auditor=StubCoverageAuditor(),
        )
        rc = run_cli_with_roles(ass_file, tmp_path / "assets", roles, "needs_review_exit_roles")
        assert rc == 0


# ---------------------------------------------------------------------------
# 触界行为（明确不含 / 全局错误初始清单——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestFailureIsolationBoundaries:
    def test_base_exception_not_isolated_aborts_run(self, three_source_corpus, tmp_path):
        """非隔离边界（票内裁定）：BaseException（如人为中断
        KeyboardInterrupt）不是 Source 局部错误——不得被隔离吞成
        failed Source，必须中止整次运行且不产出产物。"""

        roles = CognitiveRoles(
            extractor=_ExtractorInterruptOnEp02(
                script={
                    "ep01": make_units_with_time_range(),
                    "ep03": make_ep03_units(),
                }
            ),
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        asset_dir = tmp_path / "assets"
        with pytest.raises(KeyboardInterrupt, match="受控：人为中断"):
            run_cli_with_roles(three_source_corpus, asset_dir, roles, "interrupt_stub_roles")
        assert not (asset_dir / "run-summary.md").exists()

    def test_usage_error_exit_code_2(self, tmp_path):
        """退出码契约（票内裁定）：用法错误 = 2（argparse 标准）——与
        0/1/3 三个运行类退出码互斥可辨。"""

        from subtitle_forge.cli import main

        with pytest.raises(SystemExit) as excinfo:
            main([])
        assert excinfo.value.code == 2

    def test_corpus_load_failure_global_abort(self, tmp_path, capsys):
        """全局错误初始判据 (a)（票内裁定）：Corpus 装载失败 → 全局中止
        （退出码 3）。fixture：损坏符号链接的 .ass——glob 命中而读取
        失败，确定性且不依赖运行用户权限。"""

        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        (corpus_dir / "broken.ass").symlink_to(corpus_dir / "nonexistent-target")

        from subtitle_forge.cli import main

        asset_dir = tmp_path / "assets"
        rc = main(["run", str(corpus_dir), str(asset_dir)])
        assert rc == 3
        assert "全局错误" in capsys.readouterr().err
        assert not (asset_dir / "run-summary.md").exists()

    def test_stub_factory_bad_return_global_abort(self, three_source_corpus, tmp_path, capsys):
        """全局错误初始判据 (b) 的完整形态（票内裁定）：替身工厂存在但
        产物不是认知角色集 → 运行级装配失败，全局中止（退出码 3），
        不得放行成逐 Source 失败的 execution_failure 假象。"""

        mod = types.ModuleType("bad_factory_stub_roles")
        mod.stub_roles = lambda: None  # type: ignore[attr-defined]
        sys.modules["bad_factory_stub_roles"] = mod
        from subtitle_forge.cli import main

        asset_dir = tmp_path / "assets"
        rc = main(
            [
                "run",
                str(three_source_corpus),
                str(asset_dir),
                "--stub-module",
                "bad_factory_stub_roles",
            ]
        )
        assert rc == 3
        assert "全局错误" in capsys.readouterr().err
        assert not (asset_dir / "run-summary.md").exists()

    def test_stub_module_load_failure_global_abort(self, three_source_corpus, tmp_path, capsys):
        """全局错误初始清单（票内裁定）：替身模块装载失败属运行级装配
        错误 → 全局中止（退出码 3），不产出任何产物。"""

        from subtitle_forge.cli import main

        asset_dir = tmp_path / "assets"
        rc = main(
            [
                "run",
                str(three_source_corpus),
                str(asset_dir),
                "--stub-module",
                "nonexistent_stub_module_07",
            ]
        )
        assert rc == 3
        assert "全局错误" in capsys.readouterr().err
        assert not (asset_dir / "run-summary.md").exists()
