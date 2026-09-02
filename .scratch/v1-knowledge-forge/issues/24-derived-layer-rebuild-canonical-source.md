# 24 — 衍生层可重算与唯一规范源

**What to build（单一产品增量）:** 衍生层具备最小真实内容（由各 Source 规范资产派生的跨 Source 结构，如全 Corpus 索引/目录），删除后可一键重建；基础层与可信发布集不变；衍生物只由规范源派生（无反向编辑通道）。

**Spec anchors:** R2.6/R2.7、R6.2/R6.5/R6.6、A10、A21。

**Blocked by（硬依赖）:** 10（reader）、18、19（内容形态稳定后再定派生结构）。25 前实施。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 21（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 删除 `derived/` → 执行重建入口 → 内容复原（与删除前等价）
- [ ] 重建前后 `sources/` 与 trusted-set 字节不变
- [ ] 无双向漂移通道（修改派生物不被当作规范源变更——重建即覆盖，A21 断言形态）

**Implementation / code anchors:** `assets.py` derived 占位目录；重建入口（CLI 形态票内裁定）。

**明确不含（触界行为）:** 跨 Source 知识归并/矛盾检测等衍生知识能力（裁决 5：V1 不要求）；索引/缓存技术复杂化（可删、可重建即达标）。

**票内裁定:** 衍生层最小内容形态；重建入口形态。**实现约束：重建一律经 10 票 canonical reader 取数**，不另写对当前 Markdown+JSON 临时格式的解析——若 25 迁移格式，reader 是唯一需要跟随改动的读取点。

**Spec 覆盖责任:** A10、A21；R2.6/R2.7、R6.2/R6.5/R6.6。
