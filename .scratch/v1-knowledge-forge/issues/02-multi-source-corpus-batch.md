# 02 — Corpus 批处理：多 Source 顺序完成，互不污染

**What to build（单一产品增量）:** 一个 Corpus 目录含 ≥2 个合法 ASS Source，一次 `run` 全部顺序处理完成；每个 Source 各自产出忠实层资产，可信发布集与运行摘要覆盖全部 Source 且归属正确；任何 Source 的知识单元不会出现在另一 Source 的产物中。

**Spec anchors:** R1.1（Corpus 为批处理单位）、R6.4（资产与 Source 明确对应）、A3（单次运行内全量对账的部分）。

**Blocked by（硬依赖）:** None — can start immediately（Ticket 01 之后即可开始）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 02（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 两个 Source，一个 stub module（`StubExtractor.script` 同时含 ep01、ep02 各自的独立脚本条目）→ 退出码 0；`asset_organization` 清单中两个 Source 的忠实层资产各就各位
- [ ] 每份忠实层资产的 unit_id 集合与该 Source 的脚本精确一致；trusted-set 按 `source_id` 分组后的集合分别与两份脚本一致，条目总数 = 两组之和
- [ ] run-summary 两个 Source 均 `success`，各自单元状态齐全；gap-report 为空

**Implementation / code anchors:** `cli.py` 多 Source 拒绝守卫（Ticket 01 基线 64–73 行）；`assets.write_all` 单 Source 签名（基线 233 行起）；`pipeline.run_corpus` 已按 Source 循环（预计不改）。

**明确不含（触界行为）:** Source 失败隔离——任一 Source 异常仍使整次运行失败（fail loud，07 票落隔离）；运行范围控制——仍只有全量一种请求形态（09 票）；跳过/幂等——每次全量重处理（10/11 票）；空 Corpus 仍明确拒绝（维持现状，不在本票改变）。

**票内裁定:** 批处理顺序语义（现状为文件名序、确定性，确认即可）；触及文件注释中残留的废弃编号引用顺手清理（改为 Spec/ADR 条款引用，约定见 ADR-0007）。

**Spec 覆盖责任:** A3（运行内全量对账部分）；R1.1、R6.4 的端到端断言。
