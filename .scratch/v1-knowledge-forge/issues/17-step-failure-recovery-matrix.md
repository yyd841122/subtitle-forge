# 17 — 关键步骤失败后的独立恢复矩阵（A7 收口）

**What to build（单一产品增量）:** 对**同一失败基线**，A7 要求的两种触发各自独立成立：(i) 仅重跑该 Source（全流程）；(ii) 仅重跑该关键步骤（16 形态）；且失败结果不被跳过逻辑当作已完成。

**Spec anchors:** A7（完整收口）、R5.1/R5.2。

**Blocked by（硬依赖）:** 09、16、11、12（source-only 恢复是对已有资产目录的范围运行，该形态由 12 开放）。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 14b（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:** 注入审查步骤对某 Source 失败（前次运行该 Source `failed`，其余成功）→
- [ ] (i) source-only 重跑：仅该 Source 全流程重处理，成功，其余引用既有
- [ ] (ii) step-only 重跑：audit-only 请求（extractor tripwire 验证未重提炼），成功
- [ ] 两路径最终产物内容等价；前次失败未被任何路径当作「已完成」复用（联动 11 四要素）

**Implementation / code anchors:** 09 + 16 + 11 的组合验收（本票主要是矩阵补齐与 A7 的完整断言）。

**明确不含（触界行为）:** 更完整的重跑请求矩阵（extract-only 等——真实需要时另立票）。

**票内裁定:** 无新增 How；若矩阵补齐中发现缺口，记录并最小化处理。

**Spec 覆盖责任:** A7（完整收口）；R5.1/R5.2。
