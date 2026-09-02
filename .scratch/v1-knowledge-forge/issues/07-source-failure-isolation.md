# 07 — Source 失败隔离与继续批处理

**What to build（单一产品增量）:** 某 Source 的处理抛错（替身脚本注入）→ 该 Source `failed`、缺口报告 `execution_failure` 条目、其余 Source 照常完成、运行结束可辨部分失败；全局性错误仍中止整批。

**Spec anchors:** R4.6（Source 失败）、R4.2、R5.5、A3（注入失败部分）、A11（execution_failure 部分）。

**Blocked by（硬依赖）:** 02。

**Status:** in progress (2026-09-02 开工；票内裁定已落，见下方记录)

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

> 票内裁定落定记录（2026-09-02 开工即落）：
> - **Open Impl 13 初始判据（Source 局部 vs 全局）**：
>   - *Source 局部错误（隔离）*：单个 Source 处理作用域内抛出的一切
>     `Exception`——提炼调用、单元级审查循环（含 03/05 票守卫：拒绝缺
>     理由 / 待复核缺理由 / 结论值域外）、忠实性程序门、覆盖审计调用。
>     理由：守卫的不变量是「不产出语义不完整的半成品条目」，隔离后仍
>     绝对成立（守卫异常 → 该 Source 无任何单元下落，不产生缺原因条目）；
>     守卫异常本质上是「该 Source 的处理抛错」的一种（R4.6：流程无法
>     完整完成 → failed），03/05 票的 fail loud 语义收窄为本 Source 内
>     失败，不再中止整批。`BaseException`（KeyboardInterrupt 等）不经
>     隔离，维持中止。
>   - *全局错误（中止）*：(a) Corpus 装载失败与空 Corpus（R1.1 批处理
>     单位不成立）；(b) 替身模块装载失败（运行级装配）；(c) 资产落盘
>     失败（`write_all` 抛错，含 AC 钉死的「资产目录不可写」fixture——
>     输出阶段，无法形成完整产物集）。清单完备化明确不在本票。
> - **退出码契约**：0 = 运行完成且无 failed Source（success /
>   needs_review 均为已完成的下落，R4.6 三态不混用，needs_review 不是
>   运行失败）；1 = 运行完成但存在 ≥1 failed Source（部分失败，AC2 的
>   具体退出码）；2 = 用法错误（argparse 标准，维持）；3 = 全局中止
>     （运行未完成、无完整产物集）。空 Corpus 退出码由 1 改 3：02 票
>     「空 Corpus 明确拒绝」语义不变，退出码并入本票的全局中止族——
>     机器可辨「运行完成但有缺口」（查产物）与「运行未完成」（重跑）。
> - **报告形态**：部分失败由四层承载——退出码 1；stdout 明确「部分
>   失败」并列出失败 Source id；run-summary 每 Source 状态（failed +
>   reason）；gap-report `execution_failure` 条目（含原因与下落）。
> - **失败 Source 的原子性**：Source failed ⇒ 该 Source 无单元记录、
>   无忠实层资产、其任何单元不进发布集（含失败发生前已通过审查的
>   单元——R4.6「无法形成符合规格要求的 Source 结果」，半成品整体
>   作废；`execution_failure` 条目是其唯一留痕，无静默消失由运行摘要
>   的 Source 状态承担，A3）。
> - **失败 Source 不写忠实层资产**：忠实层语义是「忠实表达来源内容」
>   的提炼产物；为失败 Source 写空资产会与「提炼完成但产出为空」（08
>   票保守提炼场景）不可辨。其下落由运行摘要 + 缺口报告显性承载。
