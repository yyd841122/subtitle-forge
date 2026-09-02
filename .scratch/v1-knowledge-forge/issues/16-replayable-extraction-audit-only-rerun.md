# 16 — 可回放提炼结果与 audit-only 重跑

> 本票引入**提炼中间产物（extraction envelope）**：按 Source 持久化的审前中间态（提炼角色的完整输出：候选单元 + 提炼信号）。与 10 票快照的区别：envelope 记录**输入给审查的东西**，快照记录**最终结局**。envelope 是可弃中间产物（R6.2 精神：丢失则回退全流程重跑，不属规范资产——票内裁定生命周期，须记录）。

**What to build（单一产品增量）:** 运行请求可「仅重跑指定 Source 的审查步骤」：复用既有 envelope，不调用提炼角色；审查结论变化自然更新结局快照与全局产物。

**Spec anchors:** A7（步骤级触发形态）、R5.1/R5.3、Implementation Decisions 1 不变量（关键步骤可独立恢复/重算）。

**Blocked by（硬依赖）:** 09（Source 选择形态）、10（快照基础设施）、11（全局产物重建机制——audit-only 后的重建复用它，不另实现）。软依赖/顺序建议：14（默认版本下即可成立）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 14a（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 提炼替身设为**被调用即抛错**的 tripwire（`fail_on_unscripted` 同形态——audit-only 场景下任何 Source 都不在脚本中）；audit-only 请求**成功完成**本身就是「提炼未被调用」的外部可观察证据（不需要计量或字节推断）
- [ ] audit-only 运行后：该 Source 快照按新审查结论更新、全局产物重建正确；与一次全流程成功运行的内容等价
- [ ] envelope 版本与请求版本不一致 → 明确拒绝（比对 envelope 记录的版本字段）；envelope 缺失 → 明确回退提示（拒绝执行而非静默全流程，票内裁定措辞）

**Implementation / code anchors:** 提炼角色输出结构的持久化（新中间产物）；运行请求增加步骤目标；管线从 envelope 续跑审查。

**明确不含（触界行为）:** 失败恢复的组合场景收口（17）；extract-only 请求、发布重建等其余矩阵（本票只落 audit-only 一个最小可用步骤）。

**票内裁定:** Open Impl 6 envelope 形态与生命周期；audit-only 请求的参数形态。实现约束：envelope 的读取经与 10 票 canonical reader 同层的统一读取通道扩展完成，不另写一次性解析路径。

**Spec 覆盖责任:** A7（步骤级触发形态）；R5.1/R5.3。
