# 0006 — Ticket 01 实现决策：运行时、CLI 入口、替身注入、单元 schema 与规范源初始形态

已接受（2026-09-02，Ticket 01 裁定）。

Ticket 01 对五项 Open Implementation Decisions 作初始裁定。除规范源格式（15 票可修正迁移）外，这些裁定是可演进的实现选择而非产品约束——后续票按接缝验收，不因内部替换而违反规格。

## 1. 语言与运行时（Open Impl 18）

**决策：Python 3.11+，纯标准库，零运行时第三方依赖；pytest 作为唯一 dev 依赖；setuptools + `src/` 布局，editable 安装。**

理由：单人本地工具、单文件输入解析与 JSON/Markdown 产物，标准库完全够用；零依赖使"资产不依赖本系统存活"（R6.1）在工具链层面也更稳。AI 环节（13/14 票）接入真实模型时按需引入模型 SDK——那是加法，不推翻本裁定。

## 2. CLI 最小入口（Open Impl 1）

**决策：单一命令 `subtitle-forge run <corpus_dir> <asset_dir> [--stub-module MODULE]`，仅 Ticket 01 所需的全量单 Source 运行形态。**

批处理范围控制（全量/指定 Source）、阶段重跑、受限配置等入口由 02/11/12 票按验收需要扩展；命令命名与参数形态此时不锁死。`--stub-module` 指向暴露 `stub_roles() -> CognitiveRoles` 的 Python 模块——替身注入是测试输入的一部分（Testing Decisions），CLI 暴露该通道使端到端接缝（含运行请求）完整可驱动。

## 3. 替身注入机制（Open Impl 12）

**决策：认知角色以 Protocol 接口（提炼 `ExtractionRole` / 推理审计 `InferenceAuditRole` / 覆盖审计 `CoverageAuditRole`）定义；确定性替身（`StubExtractor` 等）与真实模型实现同一接口，经 `CognitiveRoles` 组合注入，按角色独立替换。**

- 替身行为是纯数据脚本（按 source_id / unit_id 预设），测试对每个角色分别设定行为。
- `StubExtractor.fail_on_unscripted`：脚本外 Source 被调用即抛错——供 11 票"不重复处理"oracle 复用。
- 角色调用按角色名计量（运行摘要 `role_call_counts`）——12 票计量契约的最小雏形，替身与真实调用共用同一语义。

## 4. 知识单元 schema 与 Source Reference locator（Open Impl 15）

**决策：`KnowledgeUnit = unit_id + unit_type + statement + source_reference (+ extraction_doubts)`；`SourceReference = segment_id + quoted_text + locator`；locator 为带 `kind` 的开放 union（`time_range` / `text_position`），时间区间只是 V1 ASS 实例的取值，不是必填语义。**

- `unit_type` 开放集合（claim/method/explanation/case/argument/conclusion，可增不改）——R2.2 类型不限于 Claim。
- locator 各类型自带字段（time_range: start_ms/end_ms；text_position: segment_id/char_start/char_end），`kind` 判别；结构上保留非时间定位类型的表达空间（R1.4 未来兼容约束，Q26——V1 不验收无时间轴输入，但 schema 不锁死）。
- `extraction_doubts` 承载提炼疑点**信号**（裁决 4：信号不等于正式 Review Note；确认与产出入审查环节，09 票）。

## 5. 规范源格式初始形态（Open Impl 7）

**决策：人可读 Markdown 为主 + 结构内嵌 JSON 代码块（```json）。目录组织承载两个正交层分离：`sources/<source_id>/knowledge-units.md`（忠实层、基础层，每 Source 独立成立）；`review/`（审查层，系统判断）；`derived/`（衍生层，可整体重算）；全局产物 `trusted-set.md` / `gap-report.md` / `run-summary.md`。**

人直接可读（Markdown 标题与说明）与机器可程序化解析（JSON 代码块）同文件满足（R6.3）；时间戳类运行元数据单独成行（`run-metadata:` 前缀），内容比对可排除（为 10 票 A5 预留）。本形态是**初始裁定**：15 票对规范源格式作最终裁定并验收，若冲突在该票内完成迁移。

## 值域约定（随本 ADR 固化）

实体状态与缺口类别的字符串值域（外部产物中的可观察取值）：Source 级 `success`/`failed`/`needs_review`；Knowledge Unit 级 `passed`/`rejected`/`needs_review`/`failed`；Gap Category `execution_failure`/`audit_rejection`/`coverage_concern`/`warning`。

## 备择方案

- **运行时**：Node/TS（生态对 LLM SDK 友好，但用户环境以 Python 为主，且解析/产物层无依赖优势）；Rust（性能无此规模需求）。均不取。
- **规范源**：纯 JSON/YAML（机器优）或纯 Markdown 无结构块（人优）——单一形态难以同时满足 R6.3 双一级消费者；JSON 为主 + Markdown 派生则派生通道在 15 票前就需建设。内嵌混合是初始成本最低的双读形态。
- **替身机制**：环境变量/配置文件注入——不如模块注入直接可控，且与"替身脚本是纯数据"的断言需求耦合差。

## 后续票对本 ADR 的既定关系

- 15 票：规范源格式最终裁定（可迁移本条 5）。
- 03/04 票：非通过结论与无引用单元的下落语义（本票以 fail-loud 挡板划界，不产出语义错误的半成品产物）。
- 12 票：角色计量契约展开（本票 role_call_counts 为雏形）。
