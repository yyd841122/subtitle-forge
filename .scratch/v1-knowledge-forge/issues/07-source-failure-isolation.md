# 07 — Source 失败隔离与继续批处理

**What to build（单一产品增量）:** 某 Source 的处理抛错（替身脚本注入）→ 该 Source `failed`、缺口报告 `execution_failure` 条目、其余 Source 照常完成、运行结束可辨部分失败；全局性错误仍中止整批。

**Spec anchors:** R4.6（Source 失败）、R4.2、R5.5、A3（注入失败部分）、A11（execution_failure 部分）。

**Blocked by（硬依赖）:** 02。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 07（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 三 Source、第二个提炼替身抛错 → ep01/ep03 正常产出且发布集含其单元；ep02 `failed` + gap `execution_failure` 条目（含原因）
- [ ] 退出码非 0 且输出可辨部分失败（具体退出码票内裁定并断言）；全部 Source 均有状态（无静默消失）
- [ ] 全局错误场景钉死一个具体 fixture（资产目录不可写）→ 明确中止，无半成品全局产物

**Implementation / code anchors:** `pipeline.run_corpus` 的 Source 循环（Ticket 01 基线无隔离，异常直接冒泡）；`cli.py` 错误输出。

**明确不含（触界行为）:** 失败 Source 的重跑语义（09/11 票——本票失败后重跑即全量重处理）；全局错误判定清单的完备化（票内只裁初始判据）。

**票内裁定:** Open Impl 13 初始清单（Source 局部错误 vs 全局错误的判据）；部分失败的退出码/报告形态。

**Spec 覆盖责任:** A3（注入失败部分）、A11（execution_failure）、A4（failed 状态）；R4.6、R5.5。

> 保留与 02 的分拆：02 先建立正常批处理形态，07 只加失败隔离语义。
