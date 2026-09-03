"""CLI 最小入口（Open Impl 1 的裁定，ADR-0006）：仅当前运行请求所需。

    subtitle-forge run <corpus_dir> <asset_dir> [--source ID[,ID…]] [--stub-module MODULE]

Corpus 批处理：一次 run 顺序处理目录内全部 Source（R1.1，票 02）——
这是 --source 省略时的默认行为；指定 --source 时仅处理被选子集（见下）。
Source 失败隔离（07 票）：单个 Source 的处理抛错只使该 Source failed
（缺口 execution_failure、摘要留痕），其余 Source 照常完成，运行以
部分失败结束；全局性错误（R5.5）中止整批。替身注入是测试输入的一部分
（Testing Decisions）：--stub-module 指向的 Python 模块暴露
``stub_roles() -> CognitiveRoles``，管线据此组装认知角色集；不指定时
使用通过路径的默认替身（真实角色接入属 27/28 票）。

运行范围控制（09 票，R5.1/R5.2、A7 触发形态、A12 控制手段）：--source
以逗号分隔的 id 列表指定 Source 子集，仅被选 Source 进入处理；未选
Source 本次完全不触碰（忠实层资产不创建、其解析观察不产生）——范围
控制成为可观察的成本控制手段。load_corpus 仍装载全量（02 票语义），
过滤在运行请求层完成；批内处理顺序维持文件名序（选择是成员资格，
不重排）。范围运行仅面向全新资产目录：对已有资产目录的范围运行触界
明确拒绝（fail loud）——「未选 Source 引用既有产出」的表达由后续票
落定后自然开放，本票不固化与 R4.3/A3 相抵的临时语义。

退出码契约（07 票票内裁定）：

    0  运行完成，无 failed Source（success / needs_review 均为已完成的
       下落，R4.6 三态不混用——needs_review 不是运行失败）
    1  运行完成（产物完整），但存在 ≥1 failed Source（部分失败，
       stdout 列名失败 Source）
    2  用法错误（argparse 标准）
    3  全局中止：运行未完成、无完整产物集（Corpus 装载失败/空 Corpus、
       替身模块装载失败、资产落盘失败——Open Impl 13 初始判据；09 票
       增判据：范围请求校验失败——选不存在的 Source id、范围运行触碰
       已有资产目录）
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from pathlib import Path

from .artifacts import SOURCE_STATUS_FAILED
from .assets import write_all
from .ass import load_corpus
from .model import Corpus
from .pipeline import run_corpus
from .roles import CognitiveRoles, StubCoverageAuditor, StubExtractor, StubInferenceAuditor

# 退出码契约（07 票票内裁定，见模块 docstring）。
EXIT_OK = 0
EXIT_PARTIAL_FAILURE = 1
EXIT_GLOBAL_ABORT = 3


def _default_stub_roles() -> CognitiveRoles:
    """默认替身：产出空（无脚本），通过路径形态——真实运行前须显式注入
    或接入真实角色（27 票）。fail_on_unscripted 关闭，避免空跑崩溃。"""

    return CognitiveRoles(
        extractor=StubExtractor(script={}, fail_on_unscripted=False),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


# 认知角色集的最小装配契约：每个角色成员须实现其接口方法（Protocol
# 的运行时最小校验——完整装配失败是运行级问题，全局中止而非逐 Source
# 失败的 execution_failure 假象）。每项：角色成员名、接口方法、方法
# 的位置参数个数（按位预检——bind 只验证可调用形态，不执行）。
_ROLE_INTERFACE = (
    ("extractor", "extract", 1),
    ("inference_auditor", "audit_unit", 2),
    ("coverage_auditor", "audit_coverage", 2),
)


def _validate_role_member(module_name: str, role_name: str, member, method: str, arity: int) -> None:
    """单成员装配校验：非类、非协程函数、方法可按接口元数调用。"""
    if member is None:
        raise RuntimeError(
            f"替身模块 {module_name!r} 的认知角色集不完整：{role_name} 缺失"
        )
    if isinstance(member, type):
        raise RuntimeError(
            f"替身模块 {module_name!r} 的 {role_name} 传入了类而非实例：{member!r}"
        )
    bound = getattr(member, method, None)
    if not callable(bound):
        raise RuntimeError(
            f"替身模块 {module_name!r} 的认知角色集不完整："
            f"{role_name} 缺少可用的 {method}() 接口"
        )
    if inspect.iscoroutinefunction(bound):
        raise RuntimeError(
            f"替身模块 {module_name!r} 的 {role_name}.{method}() 是协程函数，"
            "与同步管线不兼容"
        )
    try:
        inspect.signature(bound).bind(*([None] * arity))
    except TypeError as exc:
        raise RuntimeError(
            f"替身模块 {module_name!r} 的 {role_name}.{method}() 与接口元数"
            f"不符（需 {arity} 个位置参数）：{exc}"
        ) from None


def _load_stub_roles(module_name: str) -> CognitiveRoles:
    module = importlib.import_module(module_name)
    factory = getattr(module, "stub_roles", None)
    if not callable(factory):
        # 运行级装配错误（全局中止族，07 票初始判据）——抛普通异常，
        # 由 main 的全局错误处置统一转 stderr + 退出码 3。
        raise RuntimeError(f"替身模块 {module_name!r} 未暴露 stub_roles() -> CognitiveRoles")
    roles = factory()
    if not isinstance(roles, CognitiveRoles):
        # 同族装配错误：工厂存在但产物不是完整认知角色集——放行会让
        # 缺角色的运行逐 Source 失败（execution_failure 假象），而装配
        # 缺陷是运行级问题，应全局中止（07 票初始判据 (b) 的完整形态）。
        raise RuntimeError(
            f"替身模块 {module_name!r} 的 stub_roles() 返回 {type(roles).__name__}，"
            "不是 CognitiveRoles 认知角色集"
        )
    for role_name, method, arity in _ROLE_INTERFACE:
        _validate_role_member(module_name, role_name, getattr(roles, role_name, None), method, arity)
    return roles


def _global_abort(stage: str, exc: Exception) -> int:
    """全局错误处置（07 票，R5.5）：stderr 可辨中止原因，退出码 3——
    与「运行完成但有缺口」（部分失败，1）在机器层面可区分。"""

    print(f"运行中止（全局错误）——{stage}：{type(exc).__name__}：{exc}", file=sys.stderr)
    return EXIT_GLOBAL_ABORT


def _parse_source_selection(value: str) -> tuple[str, ...]:
    """``--source`` 的取值解析（09 票票内裁定：``id[,id…]`` 形态）。

    空值或含空 token（如 ``ep01,,ep02``）是用法错误（argparse 标准，
    退出码 2）——解析层即拒绝，不进入运行；id 是否存在于 Corpus 属
    请求语义校验，须待 Corpus 装载后在 main 里判定（fail loud，退出码 3）。
    """

    ids = tuple(value.split(","))
    if any(not token for token in ids):
        raise argparse.ArgumentTypeError(
            f"无效的 Source 选择 {value!r}：须为逗号分隔的非空 id 列表（如 ep01,ep02）；"
            "省略本参数则为全量运行"
        )
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="subtitle-forge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="对一个 Corpus 目录执行端到端运行")
    run_parser.add_argument("corpus_dir", type=Path, help="含 .ass Source 文件的目录")
    run_parser.add_argument("asset_dir", type=Path, help="资产输出目录")
    run_parser.add_argument(
        "--source",
        type=_parse_source_selection,
        default=None,
        metavar="ID[,ID…]",
        help="运行范围：仅处理指定的 Source（逗号分隔）；省略则为全量运行",
    )
    run_parser.add_argument(
        "--stub-module",
        type=str,
        default=None,
        help="确定性替身模块（暴露 stub_roles()），测试注入点",
    )

    args = parser.parse_args(argv)
    if args.command != "run":  # pragma: no cover - argparse 已保证
        return 2

    # —— 范围请求校验 (a)（09 票触界，fail loud）——范围运行仅面向
    # 全新资产目录：触碰已有目录即拒绝（运行未开始，全局中止族）。
    # 以「目录是否存在」为界，不定义"什么算资产目录"的临时语义。
    if args.source is not None and args.asset_dir.exists():
        print(
            f"范围运行拒绝：资产目录已存在，本票范围运行仅面向全新资产目录："
            f"{args.asset_dir}",
            file=sys.stderr,
        )
        return EXIT_GLOBAL_ABORT

    # —— 全局错误初始判据 (a)：Corpus 装载（07 票，Open Impl 13）——
    try:
        corpus = load_corpus(args.corpus_dir)
    except Exception as exc:
        return _global_abort("Corpus 装载失败", exc)
    # 空 Corpus 明确拒绝（R1.1：Corpus 是批处理单位，空批不构成一次
    # 运行；不静默产出"空跑成功"的产物）——同属全局中止族（运行未
    # 开始）。≥1 个 Source 即顺序批处理（文件名序、确定性，票内裁定）。
    if len(corpus.sources) == 0:
        print(f"corpus 目录无 .ass Source：{args.corpus_dir}", file=sys.stderr)
        return EXIT_GLOBAL_ABORT

    # —— 范围请求校验 (b)（09 票）：选中的 id 必须都存在于 Corpus——
    # 要么整体成立、要么不开始（不静默降级为「处理存在的那些」）。
    # 过滤在运行请求层完成（load_corpus 仍装载全量）；处理顺序维持
    # 文件名序（选择是成员资格，不重排）。
    if args.source is not None:
        known_ids = {s.source_id for s in corpus.sources}
        unknown_ids = [sid for sid in args.source if sid not in known_ids]
        if unknown_ids:
            print(
                f"范围运行拒绝：选中的 Source 不存在于 Corpus：{'、'.join(unknown_ids)}"
                f"（可用：{'、'.join(sorted(known_ids))}）",
                file=sys.stderr,
            )
            return EXIT_GLOBAL_ABORT
        selected = set(args.source)
        corpus = Corpus(
            sources=tuple(s for s in corpus.sources if s.source_id in selected)
        )

    # —— 全局错误初始判据 (b)：替身模块装载（07 票，Open Impl 13）——
    try:
        roles = (
            _load_stub_roles(args.stub_module)
            if args.stub_module
            else _default_stub_roles()
        )
    except Exception as exc:
        return _global_abort("替身装载失败", exc)

    # Source 局部错误已在管线下游隔离（07 票）；此处逃逸的异常 =
    # 作用域之外的问题，维持 fail loud（不吞栈，不假装成可辨状态）。
    outcome = run_corpus(corpus, roles)

    # —— 全局错误初始判据 (c)：资产落盘（07 票，Open Impl 13）——
    # 输出阶段失败影响整批（无法形成完整产物集），中止且不产出
    # 半成品全局产物（落盘首个写动作即抛错时目录保持空）。
    try:
        write_all(
            args.asset_dir,
            corpus.sources,
            outcome.source_units,
            outcome.trusted_set,
            outcome.gap_report,
            outcome.run_summary,
        )
    except Exception as exc:
        return _global_abort("资产落盘失败", exc)

    failed_ids = [
        r.source_id for r in outcome.run_summary.sources if r.status == SOURCE_STATUS_FAILED
    ]
    if failed_ids:
        # 部分失败（07 票）：运行完成、产物完整，输出可辨部分失败
        # （stdout 明示并列出失败 Source——机器与人都无需翻产物即可辨）。
        print(
            f"运行完成（部分失败）：{len(corpus.sources)} 个 Source，"
            f"发布集 {len(outcome.trusted_set.entries)} 单元；"
            f"失败 Source：{'、'.join(failed_ids)}"
        )
        return EXIT_PARTIAL_FAILURE
    print(
        f"运行完成：{len(corpus.sources)} 个 Source，"
        f"发布集 {len(outcome.trusted_set.entries)} 单元"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
