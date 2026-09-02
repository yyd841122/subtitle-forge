# 08 — 噪声容忍的确定性验收（解析级显性化 + 内容级容忍）

**What to build（单一产品增量）:** 噪声与解析异常**不使处理失败、且显性可观察**：(a) 解析级——被跳过的畸形行/空文本事件以 `warning` 缺口条目显性化（含 Source、跳过原因、下落「不影响处理」）；(b) 内容级——含口头填充、重复、轻微转写错误的 Source 端到端处理不失败，噪声文本不出现在知识单元（替身脚本化：脚本单元只锚定知识性 Segment），正常知识照常提炼。这是 **A13 的确定性验收形态**。

**Spec anchors:** R1.3、A11（warning 类）、A13（确定性半边）、R4.2。

**Blocked by（硬依赖）:** None（`GapEntry` 结构自 Ticket 01 即存在；03 仅为缺口条目的实现先例，不是依赖——依赖图保持唯一顺序事实）。07 后实施更自然（批处理语境），非硬依赖。

**Status:** open（2026-09-02 materialized）

**Materialized from:** plan v2.2 票 08（ADR-0007）

**Acceptance（端到端断言，只对外部产物）:**
- [ ] 畸形 fixture 钉死两类：字段不足导致正则不匹配的行；清洗后空文本事件 → Source 不失败、知识单元照常；gap-report `warning` 条目含 source_id / reason（行号或行内容可辨）/ outcome。无效时间戳是否计入 warning 由票内裁定（当前 `_parse_ass_timestamp` 会抛异常——裁定其归属：warning 化或维持全局错误，记录理由）
- [ ] 噪声 fixture：Dialogue 含填充/重复/轻微错字的 Source → 处理不失败；断言全部知识单元的 statement 与 quoted_text 均不含噪声片段、只含知识性片段；正常单元照常进发布集
- [ ] 无畸形、无噪声的运行 warning 为空

**Implementation / code anchors:** `ass.py`（Ticket 01 基线 58/62 行的静默 skip——需把跳过信息传到运行层，承载形态票内裁定）；`conftest.py` 的受控 ASS 先例。

**明确不含（触界行为）:** 真实模型对噪声的**内容判断质量**——那是概率性行为，由 29 以非门禁 eval 覆盖，**不计入 A13 的验收声明**。

**票内裁定:** 跳过信息的承载形态（Source 模型字段 vs 解析报告结构）；无效时间戳的归属。

**Spec 覆盖责任:** A13（确定性验收）；A11（warning 条目）；R1.3、R4.2。
