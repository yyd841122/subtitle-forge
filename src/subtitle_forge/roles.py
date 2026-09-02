"""认知角色接口与确定性替身注入机制（Open Impl 12 的裁定，ADR-0006）。

按认知角色（提炼 / 推理审计 / 覆盖审计）定义接口，替身与真实模型实现
同一接口、可在同一运行中互换（Testing Decisions；真实角色接入属后续
票，Spec Implementation Decisions 5 的接线前提）。

替身注入是**测试输入的一部分**：测试对每个认知角色分别预设确定性行为，
断言仍只针对外部产物。本模块不提供任何"从外部产物窥探内部"的通道。

角色职责边界（产品不变量，Q27）：
- 提炼（Extractor）：产出候选知识单元。不自行宣告可信——覆盖自检、
  疑点只是信号（裁决 3、4）。
- 推理审计（InferenceAuditor）：判定候选单元是否可通过。生成与审查
  认知责任分离（R3.4）。
- 覆盖审计（CoverageAuditor）：独立产生覆盖结论（裁决 3）。

忠实性审计含纯程序比对部分（R3.1、Implementation Decisions 5），
不经由生成同一内容的替身自评——程序比对门在管线发布集准入前落地
（pipeline.py，A1），不经任何认知角色；本模块只承载认知角色。推理
审计替身的结论（通过/拒绝/待复核）经它确定性触发（A2、A14）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .model import KnowledgeUnit, Source


class ExtractionRole(Protocol):
    """提炼认知角色：Source → 候选知识单元（含覆盖自检信号、疑点信号）。"""

    def extract(self, source: Source) -> ExtractionOutput: ...


class InferenceAuditRole(Protocol):
    """推理审计认知角色：对单个候选知识单元给出可判定的结论。"""

    def audit_unit(self, source: Source, unit: KnowledgeUnit) -> UnitAuditVerdict: ...


class CoverageAuditRole(Protocol):
    """覆盖审计认知角色：对 Source 的知识覆盖独立给出结论（裁决 3）。"""

    def audit_coverage(self, source: Source, units: list[KnowledgeUnit]) -> CoverageVerdict: ...


# ---------------------------------------------------------------------------
# 角色输出的领域结构
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractionOutput:
    """提炼角色的输出：候选知识单元 + 提炼侧信号（只是信号，非结论）。"""

    units: tuple[KnowledgeUnit, ...]
    # 覆盖自检信号（裁决 3）：生成者自评，不作为最终覆盖结论。
    coverage_self_check: str | None = None


@dataclass(frozen=True)
class UnitAuditVerdict:
    """审查角色对单个知识单元的结论。

    通过 → 进入可信发布集候选；拒绝 → 不进入、缺口报告留"审计拒绝"
    条目（03 票已落地）；不确定 → 待复核（R4.4 严格语义：无法可靠
    判定，非低质量兜底；05 票已落地——单元 needs_review、不进发布集、
    运行摘要记录本结论的 reason）。
    """

    verdict: str  # "pass" | "reject" | "inconclusive"
    reason: str = ""


@dataclass(frozen=True)
class CoverageVerdict:
    """覆盖审计角色的结论。判定遗漏时缺口报告留"覆盖存疑"（R4.2 缺口
    类别，后续票落地）。"""

    covered: bool
    reason: str = ""


# ---------------------------------------------------------------------------
# 认知角色集：一次运行的全部 AI 认知执行者
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitiveRoles:
    """一次运行按认知角色组合的执行者集合。

    每个角色独立可替换（Testing Decisions）：测试可对每个角色分别注入
    确定性替身并分别设定行为，真实模型接入（后续票）实现同一组接口。
    """

    extractor: ExtractionRole
    inference_auditor: InferenceAuditRole
    coverage_auditor: CoverageAuditRole


# ---------------------------------------------------------------------------
# 确定性替身
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StubExtractor:
    """提炼替身：按预设脚本产出候选知识单元。

    脚本是纯数据（每个 Source 一份），测试对它有完全控制权——包括
    故意产出异常单元（无引用、假引用、保守极少产出等场景的种子，
    A1/A17 等由此确定性触发；假引用由管线程序门拦截，无引用单元的
    下落由 06 票落地）。
    """

    # source_id → 该 Source 应产出的候选单元序列。
    script: dict[str, tuple[KnowledgeUnit, ...]]
    coverage_self_check: str | None = None
    # 脚本外 Source 被调用即抛错——测试脚本与实际输入的错配守卫，
    # 防止替身静默产出空结果造成"看似通过"的假运行。
    fail_on_unscripted: bool = True

    def extract(self, source: Source) -> ExtractionOutput:
        if source.source_id not in self.script:
            if self.fail_on_unscripted:
                raise AssertionError(
                    f"提炼替身被意外调用：{source.source_id!r} 不在预设脚本中"
                )
            return ExtractionOutput(units=(), coverage_self_check=self.coverage_self_check)
        return ExtractionOutput(
            units=self.script[source.source_id],
            coverage_self_check=self.coverage_self_check,
        )


@dataclass(frozen=True)
class StubInferenceAuditor:
    """推理审计替身：按 unit_id 预设结论；未预设的单元默认通过。

    分别设定行为 = 对每个 unit_id 可独立给出 pass/reject/inconclusive。
    拒绝须带理由（缺口报告"审计拒绝"条目的来源，R4.2、A2）；不确定
    也须带理由（运行摘要 needs_review 条目的来源，R4.4、A14——理由是
    "为什么无法判定"的陈述，非系统兜底措辞）。
    """

    verdicts: dict[str, UnitAuditVerdict] = None  # type: ignore[assignment]
    default: UnitAuditVerdict = UnitAuditVerdict(verdict="pass")

    def __post_init__(self) -> None:
        if self.verdicts is None:
            object.__setattr__(self, "verdicts", {})

    def audit_unit(self, source: Source, unit: KnowledgeUnit) -> UnitAuditVerdict:
        return self.verdicts.get(unit.unit_id, self.default)


@dataclass(frozen=True)
class StubCoverageAuditor:
    """覆盖审计替身：按 source_id 预设覆盖结论；未预设默认覆盖良好。"""

    verdicts: dict[str, CoverageVerdict] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.verdicts is None:
            object.__setattr__(self, "verdicts", {})

    def audit_coverage(self, source: Source, units: list[KnowledgeUnit]) -> CoverageVerdict:
        return self.verdicts.get(
            source.source_id, CoverageVerdict(covered=True, reason="覆盖审计替身默认结论")
        )


# 替身工厂签名：测试注入点（CLI 的 --stub-fixture 参数按此取替身）。
StubFixture = Callable[[], CognitiveRoles]
