"""CLI 最小入口（Open Impl 1 的裁定，ADR-0006）：仅当前运行请求所需。

    subtitle-forge run <corpus_dir> <asset_dir> [--stub-module MODULE]

Corpus 批处理：一次 run 顺序处理目录内全部 Source（R1.1，票 02）。
请求形态仍只有全量一种——运行范围控制（指定 Source 子集）属 09 票。
替身注入是测试输入的一部分（Testing Decisions）：--stub-module 指向的
Python 模块暴露 ``stub_roles() -> CognitiveRoles``，管线据此组装认知
角色集；不指定时使用通过路径的默认替身（真实角色接入属 27/28 票）。
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .assets import write_all
from .ass import load_corpus
from .pipeline import run_corpus
from .roles import CognitiveRoles, StubCoverageAuditor, StubExtractor, StubInferenceAuditor


def _default_stub_roles() -> CognitiveRoles:
    """默认替身：产出空（无脚本），通过路径形态——真实运行前须显式注入
    或接入真实角色（27 票）。fail_on_unscripted 关闭，避免空跑崩溃。"""

    return CognitiveRoles(
        extractor=StubExtractor(script={}, fail_on_unscripted=False),
        inference_auditor=StubInferenceAuditor(),
        coverage_auditor=StubCoverageAuditor(),
    )


def _load_stub_roles(module_name: str) -> CognitiveRoles:
    module = importlib.import_module(module_name)
    factory = getattr(module, "stub_roles", None)
    if not callable(factory):
        raise SystemExit(f"替身模块 {module_name!r} 未暴露 stub_roles() -> CognitiveRoles")
    return factory()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="subtitle-forge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="对一个 Corpus 目录执行端到端运行")
    run_parser.add_argument("corpus_dir", type=Path, help="含 .ass Source 文件的目录")
    run_parser.add_argument("asset_dir", type=Path, help="资产输出目录")
    run_parser.add_argument(
        "--stub-module",
        type=str,
        default=None,
        help="确定性替身模块（暴露 stub_roles()），测试注入点",
    )

    args = parser.parse_args(argv)
    if args.command != "run":  # pragma: no cover - argparse 已保证
        return 2

    corpus = load_corpus(args.corpus_dir)
    # 空 Corpus 明确拒绝（R1.1：Corpus 是批处理单位，空批不构成一次
    # 运行；不静默产出"空跑成功"的产物）。≥1 个 Source 即顺序批处理
    # （文件名序、确定性，票内裁定）；无失败隔离——任一 Source 异常
    # 仍使整次运行失败（fail loud，07 票落隔离）。
    if len(corpus.sources) == 0:
        print(f"corpus 目录无 .ass Source：{args.corpus_dir}", file=sys.stderr)
        return 1

    roles = (
        _load_stub_roles(args.stub_module)
        if args.stub_module
        else _default_stub_roles()
    )
    outcome = run_corpus(corpus, roles)

    # 落盘：每个 Source 的忠实层资产（R6.4：资产与 Source 明确对应）+
    # 全局产物（候选单元取自运行结果，不对认知角色做二次调用）。
    write_all(
        args.asset_dir,
        corpus.sources,
        outcome.source_units,
        outcome.trusted_set,
        outcome.gap_report,
        outcome.run_summary,
    )
    print(
        f"运行完成：{len(corpus.sources)} 个 Source，"
        f"发布集 {len(outcome.trusted_set.entries)} 单元"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
