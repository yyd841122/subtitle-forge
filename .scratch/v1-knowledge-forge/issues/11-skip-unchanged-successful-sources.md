# 11 — 未变化且成功 Source 的跳过（含全局产物重建）

**What to build（单一产品增量）:** 同 Corpus（同默认版本）重跑时，输入未变且上次成功的 Source 被跳过——运行摘要以「引用既有产出」表达（不新增状态值，R4.6），processed / skipped 两类可辨；上次失败/待复核的 Source 不被跳过。全局产物（可信发布集、缺口报告、运行摘要）自此成为**可由 per-Source 快照重建的派生物**：全跳过的重跑产出与首跑内容一致的全局产物。

**Spec anchors:** R5.4、A5、A3（处理/跳过区分；对账作用域升级为「当前资产版本内全量实体」——含被跳过者）、A7 第三句（失败不被误认为已完成）。

**Blocked by（硬依赖）:** 05（needs_review 状态先于跳过语义存在）、10。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 11a（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 同输入两次全量运行 → 第二次全部 skipped；trusted-set 与 gap-report 内容与首跑一致（排除 `run-metadata:` 行）；无新旧混杂
- [ ] 上次 `failed` 的 Source（07 场景）重跑被**重新处理**（跳过四要素含「上次结局为 success」）
- [ ] 上次 `needs_review` 的 Source（05 场景）重跑同样被**重新处理**（needs_review 非 success，不满足跳过四要素——增量声明「失败/待复核不被跳过」的两半至此均有验收）
- [ ] 混合场景：先成功、后注入失败的历史下，当前版本全量对账成立（每个 Source 与单元有下落，skipped 引用既有产出，failed 有状态）

**Implementation / code anchors:** 10 票快照 + reader（判定与重建的数据源）；管线入口的逐 Source 判定。

**明确不含（触界行为）:** 输入变化的检测与局部重处理（12）；显式资产版本（14——版本因子当前平凡真）；已有资产目录上的范围请求（12 开放）。

**票内裁定:** Open Impl 4 四要素校验初始实现（指纹一致 + 版本一致〔当前平凡真〕+ 上次 success + 快照完整性标记有效）；skipped 在运行摘要中的表达形态。

**Spec 覆盖责任:** A5、A3（作用域/处理跳过区分）、A7 第三句；R5.4、R4.6（跳过=运行行为，不新增状态值）。
