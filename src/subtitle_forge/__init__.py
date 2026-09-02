"""subtitle-forge：AI 原生的批量知识提炼引擎。

V1 Ticket 01：单 Source 端到端 walking skeleton。分层与职责见 docs/PRODUCT.md、
docs/specs/v1-knowledge-forge.md 与 docs/adr/。

模块只按领域概念命名（CONTEXT.md 术语），不暴露阶段拓扑内部结构——
Q27 裁决：阶段拓扑不是产品强制架构，外部接缝只认 Corpus/Source/Knowledge
Unit 与外部产物（可信发布集、缺口报告、运行摘要）。
"""

__version__ = "0.1.0"
