# 08 — 噪声容忍的确定性验收（解析级显性化 + 内容级容忍）

**What to build（单一产品增量）:** 噪声与解析异常**不使处理失败、且显性可观察**：(a) 解析级——被跳过的畸形行/空文本事件以 `warning` 缺口条目显性化（含 Source、跳过原因、下落「不影响处理」）；(b) 内容级——含口头填充、重复、轻微转写错误的 Source 端到端处理不失败，噪声文本不出现在知识单元（替身脚本化：脚本单元只锚定知识性 Segment），正常知识照常提炼。这是 **A13 的确定性验收形态**。

**Spec anchors:** R1.3、A11（warning 类）、A13（确定性半边）、R4.2。

**Blocked by（硬依赖）:** None（`GapEntry` 结构自 Ticket 01 即存在；03 仅为缺口条目的实现先例，不是依赖——依赖图保持唯一顺序事实）。07 后实施更自然（批处理语境），非硬依赖。

**Status:** done (2026-09-03, cc-suite 全量审计 10 findings（7 修复 / 3 out-of-ticket 分流）→ Codex 独立复审 BLOCKED（1 blocking：AC1 outcome 断言未钉死修正后语义）→ 修复 → focused closure review **READY / 0 blocking**，断言只对外部产物)

**Materialized from:** plan v2.2 票 08（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [x] 畸形 fixture 钉死两类：字段不足导致正则不匹配的行；清洗后空文本事件 → Source 不失败、知识单元照常；gap-report `warning` 条目含 source_id / reason（行号或行内容可辨）/ outcome。无效时间戳是否计入 warning 由票内裁定（当前 `_parse_ass_timestamp` 会抛异常——裁定其归属：warning 化或维持全局错误，记录理由）
- [x] 噪声 fixture：Dialogue 含填充/重复/轻微错字的 Source → 处理不失败；断言全部知识单元的 statement 与 quoted_text 均不含噪声片段、只含知识性片段；正常单元照常进发布集
- [x] 无畸形、无噪声的运行 warning 为空

**Implementation / code anchors:** `ass.py`（Ticket 01 基线 58/62 行的静默 skip——需把跳过信息传到运行层，承载形态票内裁定）；`conftest.py` 的受控 ASS 先例。

**明确不含（触界行为）:** 真实模型对噪声的**内容判断质量**——那是概率性行为，由 29 以非门禁 eval 覆盖，**不计入 A13 的验收声明**。

**票内裁定:** 跳过信息的承载形态（Source 模型字段 vs 解析报告结构）；无效时间戳的归属。

**Spec 覆盖责任:** A13（确定性验收）；A11（warning 条目）；R1.3、R4.2。

> 票内裁定落定记录（2026-09-03 开工即落）：
> - **跳过信息的承载形态 = Source 模型字段**（`Source.parse_warnings:
>   tuple[ParseWarning, ...]`，`ParseWarning = (lineno, reason)`），非
>   独立解析报告结构。理由：(a) 跳过事实与所指 Source 不可分离——
>   字段随 Source 本体从解析层（`load_corpus`）流到运行层（`run_corpus`
>   产 warning 条目），无平行结构的键同步/脱钩风险；(b) 领域上 Source
>   是「可独立追溯的输入单位」（CONTEXT.md），其摄入观察是追溯的
>   一部分；(c) 默认空元组保持既有构造不变，`ParseWarning` 命名格式
>   中立（R1.2：新格式解析器复用同一观察结构）。
> - **无效时间戳的归属 = warning 化并跳过该行**（非维持全局错误）。
>   理由：(a) 单行时间戳损坏是典型转写/制作噪声，维持全局错误会让
>   一行噪声中止整批，违背 R1.3「噪声不得导致整 Source 失败」的精神；
>   (b) 备选「保留为无时间戳 Segment」超出 V1——时间区间是 V1 ASS
>   输入的验收形态，无时间轴 Segment 无法携带 V1 可验收的 Source
>   Reference locator（R1.4/Q26：文本位置定位 V1 不验收），只会在
>   V1 内制造不可准入的二等 Segment；(c) 行内容进 warning 原因——
>   被跳过的知识损失显性可审计（A11「不静默消失」的精神）。只捕获
>   `ValueError`（时间戳解析的已知失败形态：缺分隔符/非数字），其他
>   异常维持 fail loud。
> - **warning 条目与失败隔离的原子性（07×08 交互；cc-suite 审计后
>   修正）**：warning 条目在 `run_corpus` 处理作用域之外发射（逐
>   Source 处理之前）——Source 处理失败时**保留**，与
>   execution_failure 并存。理由：warning 是输入观察（解析层已成立
>   的跳过事实），不是处理产物；07 票产物性原子作废的是处理产物
>   （已处置单元下落、缺口条目、发布集条目、忠实层），对账性状态
>   保留（已知单元不静默消失）——被跳过的输入行同属"输入侧事实
>   不消失"一族，Source 失败不掩盖其解析异常（08 产品句「显性可
>   观察」）。初版裁定（随 07 原子一并作废）在 cc-suite 全量审计中
>   被指出与显性化要求冲突，采纳修正；有回归测试钉死并存形态。
> - **条目形态**：subject = `L<行号>`（所指输入行的 Source 内最具体
>   身份，与 audit_rejection 用 unit_id 同族）；reason 内嵌行号与行
>   内容（票面「行号或行内容可辨」取并集）；outcome 措辞
>   `GAP_OUTCOME_PARSE_WARNING`（含「不影响处理」，并如实陈述该行
>   不构成 Segment、其余内容照常提炼——审计修复：初版「不影响
>   知识提炼」对被跳过行自身的内容损失表述含混）。
> - **内容级噪声的确定性机制**：噪声排除完全由提炼角色锚定知识性
>   Segment 达成（替身脚本化）。系统准入门不做任何内容级噪声过滤
>   ——触界行为有专门测试钉死（逐字引用纯噪声 Segment 的单元照常
>   通过准入门），防止越界实现本票明确不含的概率性内容判断（29 票
>   eval 的领域）。
