# 02 — Corpus 与 ASS ingestion 扩展：批处理、噪声容忍、解析边界

**What to build:** 把 01 的单 Source 骨架扩展为真实的批处理形态：一个 Corpus（≥2 个 Source，含噪声输入）一次运行全部处理完毕，支持指定运行范围（全量 / 指定 Source）；ASS 解析容忍常见噪声且噪声不导致整 Source 失败，解析层对新增输入格式的接入不被架构性排除。每个 Source 独立走完 01 建立的完整端到端路径（提炼→审查→可信发布集/缺口报告→运行摘要），运行摘要覆盖 Corpus 内全部 Source。

本票是 ingestion 与批处理能力的扩展，不是纯解析器库票——完成的判定是"一个含噪声的多 Source Corpus 端到端跑通且每个 Source 有明确下落"。

**Blocked by:** 01 — 单 Source walking skeleton。

**Status:** ready-for-agent

- [ ] 多 Source 批处理：一个 Corpus（≥2 个 ASS Source）一次运行全部处理，运行摘要中每个 Source 均有实体状态
- [ ] 指定运行范围：全量 / 指定 Source 两种运行请求形态均可触发（A12 的"可设定运行范围"控制手段落点）
- [ ] 噪声容忍——处理不失败半：输入含口头填充、重复、轻微转写错误的 Source，处理不失败，正常知识照常产出（A13/R1.3 的确定性验收，提炼替身按预设契约处理噪声 Source；"噪声不进知识单元"的完整验收在同 fixture 上联合断言）
- [ ] 噪声不进知识单元：同一受控噪声 Source 上，知识单元不含口头填充、重复、轻微转写错误内容（A13/R1.3 完整确定性验收——用提炼替身 + 受控 fixture 完成，不依赖真实模型语义质量）
- [ ] 解析层可扩展：新增输入格式（其他字幕格式、纯转写文本）的接入不被架构性排除——V1 只验收 ASS，不验收其他格式（R1.2）
- [ ] Source 内 Segment 划分可定位：知识单元的 Source Reference 锚定到 Segment 粒度的原文位置（R1.1）
- [ ] 单 Source 失败不阻断其余 Source：受控构造一个解析失败的 Source，其余 Source 正常完成，失败 Source 有明确实体状态与缺口下落（局部失败的批处理语义）

> 实现决策（本票裁定并记录 ADR）：Segment 划分算法（Open Impl 14）；ASS 解析容错的具体规则；运行请求的完整命令形态（Open Impl 1）；Corpus 的组织方式（输入目录结构）。
