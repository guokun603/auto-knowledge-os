# 当前环境下 AutoKnowledgeOS 主体是可运行的本地知识闭环原型，但外部集成包 mcp、mem0、graphiti_core、qdrant_client、langgraph 未在活动 Python 中可用，相关能力应按本地 SQLite 兜底或未验证处理。

- id: 9
- type: lesson
- scope: repository
- status: published
- source_task: 2026-08-04-project-directory-analysis
- tags: audit,environment,dependencies,mcp,fallback
- created_at: 2026-08-04T19:50:00
- published_at: 2026-08-04T19:50:19

## Evidence

2026-08-04 directory analysis: unittest failed only on MCP JSON-RPC import path because ModuleNotFoundError: No module named mcp; status showed optional integrations unavailable.

## Conclusion

当前环境下 AutoKnowledgeOS 主体是可运行的本地知识闭环原型，但外部集成包 mcp、mem0、graphiti_core、qdrant_client、langgraph 未在活动 Python 中可用，相关能力应按本地 SQLite 兜底或未验证处理。
