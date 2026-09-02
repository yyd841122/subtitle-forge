# 12 — 输入变化检测与局部重处理

**What to build（单一产品增量）:** 修改一个 Source 的内容后重跑 → 仅该 Source 被重新处理（指纹不一致触发），其余 Source 产物保持不变；重建的全局产物中新旧内容不混杂（只有变化者的产物被替换）。

**Spec anchors:** R5.4（识别输入变化）、A6、A5（同版本语义的另一半）。

**Blocked by（硬依赖）:** 11。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 11b（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 改 ep02 内容重跑 → 仅 ep02 重处理（摘要 processed 仅含它），ep01/ep03 产物字节不变；重建后的 trusted-set 恰好替换 ep02 的条目、保留 ep01/ep03 的既有条目
- [ ] 已有资产目录上的范围请求自此开放：选 ep01 重跑 → ep01 processed、ep02/ep03 在摘要中以引用既有产出表达（与 skipped 同形态或票内裁定区分，记录理由）

**Implementation / code anchors:** 11 的跳过判定（指纹比对从平凡真变为真实分流）；reader 重建路径复用。

**明确不含（触界行为）:** 版本切换下的变化语义（14/15——本票版本恒为默认）；中断等价验收（13）。

**票内裁定:** 范围请求下「未选」与「跳过」在摘要中的区分表达。

**Spec 覆盖责任:** A6；R5.4（输入变化识别）。
