"""Ticket 08 验收：噪声容忍的确定性验收——解析级显性化 + 内容级容忍
（R1.3、A11、A13 确定性半边、R4.2）。

解析级（AC1）：畸形 fixture 钉死两类跳过（字段不足 → 正则不匹配；
清洗后空文本），外加票内裁定的无效时间戳（warning 化并跳过）→ Source
不失败、知识单元照常；缺口报告 warning 条目含 source_id / reason
（行号与行内容可辨）/ outcome（不影响处理）。

内容级（AC2）：Dialogue 含口头填充 / 重复 / 轻微转写错误的 Source →
处理不失败；全部知识单元的 statement 与 quoted_text 不含噪声片段、
只含知识性片段；正常单元照常进发布集。噪声排除由提炼替身脚本化达成
（单元只锚定知识 Segment）——真实角色的内容判断质量是概率性行为，
属 29 票非门禁 eval，不计入 A13 验收（票面明确不含）。

清洁（AC3）：无畸形、无噪声的运行 warning 为空。

票内裁定（见票面落定记录）：跳过信息承载形态 = Source 模型字段
``parse_warnings``（非解析报告结构）；无效时间戳 = warning 化并跳过
（非全局错误）；warning 条目在处理作用域之外发射（输入观察非处理
产物）——Source 失败时保留，与 execution_failure 并存（07 票原子性
只作废处理产物；审计后修正）。
"""

from __future__ import annotations

from pathlib import Path

from conftest import (
    MALFORMED_LINENO_EMPTY_TEXT,
    MALFORMED_LINENO_INSUFFICIENT_FIELDS,
    MALFORMED_LINENO_INVALID_TIMESTAMP,
    NOISE_FRAGMENTS,
    NOISY_SEG1_TEXT,
    make_malformed_units,
    make_noisy_units,
    make_units_with_time_range,
    noisy_seg_id,
    parse_json_block,
    run_cli_with_roles,
)

from subtitle_forge.model import KnowledgeUnit, SourceReference, TimeRangeLocator
from subtitle_forge.roles import (
    CognitiveRoles,
    StubCoverageAuditor,
    StubExtractor,
    StubInferenceAuditor,
)


def noise_free_roles(source_id: str, units) -> CognitiveRoles:
    """08 验收的默认角色集：提炼脚本锚定知识单元，审计全通过。"""

    return CognitiveRoles(
        extractor=StubExtractor(script={source_id: units}),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


def run_noise(corpus: Path, tmp_path: Path, roles: CognitiveRoles) -> tuple[int, Path]:
    """端到端执行（含落盘），返回（退出码, 资产目录）。"""

    asset_dir = tmp_path / "assets"
    rc = run_cli_with_roles(corpus, asset_dir, roles, "noise_tolerance_stub_roles")
    return rc, asset_dir


def warning_entries(asset_dir: Path) -> list[dict]:
    return [
        e
        for e in parse_json_block(asset_dir / "gap-report.md")["entries"]
        if e["category"] == "warning"
    ]


def assert_outcome_semantics(entry: dict) -> None:
    """outcome 语义钉死（审计修复的回归防护，Codex review blocking 1）：
    下落须如实三段陈述——跳过事实（不构成 Segment）、不影响处理、
    其余内容照常提炼。初版「不影响…知识提炼」的含混措辞（对被跳过行
    自身的内容损失表述失真）不得再通过这些断言。"""

    assert "不构成 Segment" in entry["outcome"]
    assert "不影响本 Source 的处理" in entry["outcome"]
    assert "其余内容" in entry["outcome"]


# ---------------------------------------------------------------------------
# AC1：解析级畸形 → warning 显性化，处理照常（端到端，只对外部产物）
# ---------------------------------------------------------------------------


class TestParseLevelWarningAcceptance:
    def test_malformed_source_does_not_fail_and_knowledge_as_usual(
        self, malformed_ass_file, tmp_path
    ):
        """AC1 主断言：含三类解析畸形的 Source 不失败（退出码 0、状态
        success），未受影响的知识行照常提炼（发布集含全部脚本单元、
        单元 passed）——R1.3：噪声不得导致整 Source 失败。"""

        rc, asset_dir = run_noise(
            malformed_ass_file, tmp_path, noise_free_roles("ep01", make_malformed_units())
        )
        assert rc == 0

        trusted = parse_json_block(asset_dir / "trusted-set.md")["entries"]
        assert {e["unit_id"] for e in trusted} == {"u-001", "u-002"}

        summary = parse_json_block(asset_dir / "run-summary.md")
        ep01 = next(s for s in summary["sources"] if s["source_id"] == "ep01")
        assert ep01["status"] == "success"  # warning 不改变实体状态（R4.4/R4.6）
        assert {u["status"] for u in ep01["units"]} == {"passed"}

    def test_insufficient_fields_line_surfaced_as_warning(
        self, malformed_ass_file, tmp_path
    ):
        """AC1 钉死类别一：字段不足导致正则不匹配的 Dialogue 行 →
        warning 条目含 source_id / reason（行号与行内容可辨）/ outcome。"""

        _, asset_dir = run_noise(
            malformed_ass_file, tmp_path, noise_free_roles("ep01", make_malformed_units())
        )
        [entry] = [
            e for e in warning_entries(asset_dir) if e["subject"] == f"L{MALFORMED_LINENO_INSUFFICIENT_FIELDS}"
        ]
        assert entry["source_id"] == "ep01"
        # 行号可辨（reason 内嵌）且行内容可辨（原文片段入 reason）
        assert f"第 {MALFORMED_LINENO_INSUFFICIENT_FIELDS} 行" in entry["reason"]
        assert "Dialogue: 0,0:00:01.00,Default" in entry["reason"]
        assert "字段" in entry["reason"]  # 跳过原因可辨（非自由文本）
        assert_outcome_semantics(entry)

    def test_empty_text_event_surfaced_as_warning(self, malformed_ass_file, tmp_path):
        """AC1 钉死类别二：清洗后空文本的事件（纯样式/绘制标记）→
        warning 条目，行号与行内容可辨，下落不影响处理。"""

        _, asset_dir = run_noise(
            malformed_ass_file, tmp_path, noise_free_roles("ep01", make_malformed_units())
        )
        [entry] = [
            e for e in warning_entries(asset_dir) if e["subject"] == f"L{MALFORMED_LINENO_EMPTY_TEXT}"
        ]
        assert f"第 {MALFORMED_LINENO_EMPTY_TEXT} 行" in entry["reason"]
        assert "fad(100,100)" in entry["reason"]  # 行内容可辨（绘制标记）
        assert "空" in entry["reason"]
        assert_outcome_semantics(entry)

    def test_invalid_timestamp_ruling_warningized_not_global_error(
        self, malformed_ass_file, tmp_path
    ):
        """票内裁定钉死：无效时间戳 → warning 化并跳过（非全局错误）。
        时间戳损坏行的知识内容不静默消失——行内容进 warning 原因
        （A11，可审计的显性损失）；整批运行照常完成（退出码 0）。"""

        rc, asset_dir = run_noise(
            malformed_ass_file, tmp_path, noise_free_roles("ep01", make_malformed_units())
        )
        assert rc == 0  # 维持全局错误会是退出码 3（07 票 Corpus 装载失败）
        [entry] = [
            e for e in warning_entries(asset_dir) if e["subject"] == f"L{MALFORMED_LINENO_INVALID_TIMESTAMP}"
        ]
        assert f"第 {MALFORMED_LINENO_INVALID_TIMESTAMP} 行" in entry["reason"]
        assert "时间戳" in entry["reason"]
        assert "栈会溢出" in entry["reason"]  # 被跳过行的知识内容可辨
        assert_outcome_semantics(entry)

    def test_warning_entry_shape_a11(self, malformed_ass_file, tmp_path):
        """A11：三条 warning 条目（三类畸形各一，无多余），四要素齐全
        （category / source_id / subject / reason / outcome），人可读
        （条目之外 Markdown 主体可读）。"""

        rc, asset_dir = run_noise(
            malformed_ass_file, tmp_path, noise_free_roles("ep01", make_malformed_units())
        )
        assert rc == 0
        warnings = warning_entries(asset_dir)
        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert len(entries) == len(warnings) == 3  # 基数先行：无其他缺口类别混入
        assert {e["subject"] for e in warnings} == {
            f"L{MALFORMED_LINENO_INSUFFICIENT_FIELDS}",
            f"L{MALFORMED_LINENO_EMPTY_TEXT}",
            f"L{MALFORMED_LINENO_INVALID_TIMESTAMP}",
        }
        assert all(e["source_id"] == "ep01" for e in warnings)
        assert all(e["reason"].strip() for e in warnings)
        for e in warnings:
            assert_outcome_semantics(e)


# ---------------------------------------------------------------------------
# AC2：内容级噪声 → 不失败、噪声不进知识单元、正常知识照常（A13 确定性半边）
# ---------------------------------------------------------------------------


class TestContentLevelNoiseAcceptance:
    def test_noisy_source_processes_without_failure(self, noisy_ass_file, tmp_path):
        """AC2 主断言：含口头填充 / 重复 / 轻微错字的 Source 端到端处理
        不失败（退出码 0、状态 success、全部单元 passed）——A13。"""

        rc, asset_dir = run_noise(
            noisy_ass_file, tmp_path, noise_free_roles("noisy", make_noisy_units())
        )
        assert rc == 0
        summary = parse_json_block(asset_dir / "run-summary.md")
        [noisy] = [s for s in summary["sources"] if s["source_id"] == "noisy"]
        assert noisy["status"] == "success"
        assert [u["unit_id"] for u in noisy["units"]] == ["u-n001", "u-n002", "u-n003"]
        assert all(u["status"] == "passed" for u in noisy["units"])

    def test_noise_fragments_absent_from_all_units(self, noisy_ass_file, tmp_path):
        """AC2：全部知识单元的 statement 与 quoted_text 均不含任何噪声
        片段（口头填充 / 重复形态 / 转写错字 / 寒暄），只含知识性片段
        （引用文本与 SEG_TEXTS 逐一对应）——噪声不作为知识进入资产
        （R1.3 后半句）。"""

        _, asset_dir = run_noise(
            noisy_ass_file, tmp_path, noise_free_roles("noisy", make_noisy_units())
        )
        trusted = parse_json_block(asset_dir / "trusted-set.md")["entries"]
        assert {e["unit_id"] for e in trusted} == {"u-n001", "u-n002", "u-n003"}

        for e in trusted:
            ref = e["source_reference"]
            for fragment in NOISE_FRAGMENTS:
                assert fragment not in e["statement"], (
                    f"{e['unit_id']} 的 statement 含噪声片段 {fragment!r}"
                )
                assert fragment not in ref["quoted_text"], (
                    f"{e['unit_id']} 的 quoted_text 含噪声片段 {fragment!r}"
                )
        # 只含知识性片段（封闭 oracle，不只排除已知片段）：statement 与
        # quoted_text 均恰为受控脚本的知识文本——未列噪声无从混入。
        expected = {
            u.unit_id: (u.statement, u.source_reference.quoted_text)
            for u in make_noisy_units()
        }
        assert {
            e["unit_id"]: (e["statement"], e["source_reference"]["quoted_text"])
            for e in trusted
        } == expected

    def test_normal_knowledge_reaches_trusted_set_as_usual(self, noisy_ass_file, tmp_path):
        """AC2 后半：正常知识照常提炼——噪声 Source 的三个单元全部进入
        可信发布集（引用逐字成立、锚定知识 Segment、类型不限于 Claim）；
        内容噪声不产生任何解析 warning（内容级 ≠ 解析级，缺口报告为空）。"""

        rc, asset_dir = run_noise(
            noisy_ass_file, tmp_path, noise_free_roles("noisy", make_noisy_units())
        )
        assert rc == 0
        trusted = parse_json_block(asset_dir / "trusted-set.md")["entries"]
        assert {e["unit_type"] for e in trusted} == {"claim", "method", "conclusion"}
        assert all(
            e["source_reference"]["segment_id"] in {"noisy#seg0002", "noisy#seg0004", "noisy#seg0006"}
            for e in trusted
        )  # 只锚定知识 Segment（噪声 Segment 无锚定）
        assert parse_json_block(asset_dir / "gap-report.md")["entries"] == []


# ---------------------------------------------------------------------------
# AC3：清洁运行 warning 为空
# ---------------------------------------------------------------------------


class TestCleanRunNoWarnings:
    def test_clean_run_has_no_warnings(self, ass_file, tmp_path):
        """AC3：无畸形、无噪声的运行 warning 为空（缺口报告整体为空
        已由 01 票 test_gap_report_empty_but_structurally_complete 钉死；
        本断言精确对应 AC3 的 warning 语义——正常格式结构不产生警告）。"""

        rc, asset_dir = run_noise(
            ass_file, tmp_path, noise_free_roles("ep01", make_units_with_time_range())
        )
        assert rc == 0
        assert warning_entries(asset_dir) == []


# ---------------------------------------------------------------------------
# 行为语义与边界（票内裁定 + 明确不含——不得提前实现或弱化）
# ---------------------------------------------------------------------------


class TestNoiseToleranceBehavior:
    def test_warnings_survive_source_failure(self, malformed_ass_file, tmp_path):
        """07×08 交互（票内裁定，审计后修正）：warning 是输入观察而非
        处理产物——Source 处理失败（提炼抛错）时其 warning 条目保留
        （被跳过的输入行不静默消失，与 07 票对账性状态同族），处理
        失败另由 execution_failure 对账；07 票原子性只作废处理产物
        （已处置单元下落、发布集条目），不掩盖输入事实。"""

        roles = CognitiveRoles(
            extractor=StubExtractor(script={}),  # ep01 未脚本化 → 提炼抛错
            inference_auditor=StubInferenceAuditor(),
            coverage_auditor=StubCoverageAuditor(),
        )
        rc, asset_dir = run_noise(malformed_ass_file, tmp_path, roles)
        assert rc == 1

        entries = parse_json_block(asset_dir / "gap-report.md")["entries"]
        assert [(e["category"], e["subject"]) for e in entries] == [
            ("warning", "L12"),
            ("warning", "L13"),
            ("warning", "L15"),
            ("execution_failure", "ep01"),
        ]

    def test_warning_does_not_change_source_status_semantics(
        self, malformed_ass_file, tmp_path
    ):
        """R4.4/R4.6 不混用：warning 是缺口类别不是实体状态——只含
        warning 的 Source 仍为 success（非 needs_review、非 failed）。"""

        rc, asset_dir = run_noise(
            malformed_ass_file, tmp_path, noise_free_roles("ep01", make_malformed_units())
        )
        assert rc == 0
        summary = parse_json_block(asset_dir / "run-summary.md")
        [ep01] = [s for s in summary["sources"] if s["source_id"] == "ep01"]
        assert ep01["status"] == "success"
        assert ep01["reason"] == ""  # warning 不注入 Source 级理由


class TestNoiseToleranceBoundaries:
    def test_system_gates_do_not_filter_noise_content(self, noisy_ass_file, tmp_path):
        """明确不含（触界行为）：系统不自行做噪声的内容判断——噪声排除
        是提炼角色的行为（本票替身脚本化；真实角色的判断质量由 29 票
        非门禁 eval 覆盖）。证明：替身故意产出一个引用纯噪声 Segment 的
        逐字单元（引用逐字成立、推理审计通过）——它照常进入发布集；
        若系统在准入门上加噪声过滤，即越界实现了本票明确不含的概率性
        内容判断。"""

        noise_unit = KnowledgeUnit(
            unit_id="u-noise-anchor",
            unit_type="claim",
            statement="今天我们开始讲递归",
            source_reference=SourceReference(
                segment_id=noisy_seg_id(1),
                quoted_text=NOISY_SEG1_TEXT,  # 纯噪声 Segment 的逐字引用
                locator=TimeRangeLocator(start_ms=500, end_ms=2000),
            ),
        )
        rc, asset_dir = run_noise(
            noisy_ass_file,
            tmp_path,
            noise_free_roles("noisy", (noise_unit,)),
        )
        assert rc == 0
        trusted = parse_json_block(asset_dir / "trusted-set.md")["entries"]
        assert [e["unit_id"] for e in trusted] == ["u-noise-anchor"]
        assert trusted[0]["source_reference"]["quoted_text"] == NOISY_SEG1_TEXT
