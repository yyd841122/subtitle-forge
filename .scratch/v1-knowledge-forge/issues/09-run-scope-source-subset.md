# 09 — 运行范围控制（指定 Source 子集）

**What to build（单一产品增量）:** 运行请求可指定 Source 子集，仅处理被选 Source；未选 Source 本次完全不触碰。范围控制成为可观察的成本控制手段。

**Spec anchors:** R5.1/R5.2、A7（Source 级重跑的触发形态）、A12（控制手段）。

**Blocked by（硬依赖）:** 02。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 09（ADR-0007）

**Acceptance（端到端断言，只对外部产物；全部限定**全新资产目录**，避免引入与 R4.3/A3 冲突的临时摘要语义）:**
- [ ] 三 Source 选其一、输出到全新资产目录 → 仅其被处理，运行摘要覆盖该 Source（作为本次资产版本的全部实体，全部 processed，无缺席者）
- [ ] 其余 Source 的既有产物未被创建或改写
- [ ] 选不存在的 id → 明确报错

**Implementation / code anchors:** `cli.py` run 参数（新增选择参数）；`load_corpus` 已加载全量，过滤在运行请求层。

**明确不含（触界行为）:** 对**已有资产目录**的范围运行——未选 Source 在运行摘要中「本次未处理、引用既有产出」的表达由 11/12 落定后自然开放；本票触界**明确拒绝**（fail loud），不固化一个与 R4.3/A3 相抵的临时语义。跳过判定（11）；关键步骤级重跑（16）。

**票内裁定:** 选择参数形态（如 `--source id[,id…]`）。

**Spec 覆盖责任:** A7（Source 级触发形态）、A12（控制手段）；R5.1/R5.2。
