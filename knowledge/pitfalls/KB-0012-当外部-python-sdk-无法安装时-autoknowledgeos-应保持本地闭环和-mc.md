# 当外部 Python SDK 无法安装时，AutoKnowledgeOS 应保持本地闭环和 MCP JSON-RPC fallback 可测试可用，同时在 status 和 README 中明确外部集成未激活；上传时只提交代码与 knowledge/，不提交 memory、vector、tasks 等本地运行态数据。

- id: 12
- type: lesson
- scope: repository
- status: published
- source_task: TASK-20260804-200715-修复知识库外部集成依赖
- tags: mcp,fallback,status,dependencies,upload
- created_at: 2026-08-04T20:22:45
- published_at: 2026-08-04T20:22:46

## Evidence

Network package installation failed safely: HTTPS PyPI attempts hit SSL EOF; unsafe HTTP trusted-host install was rejected. Code was changed so auto_kb.mcp_server supports JSON-RPC fallback import without external mcp SDK; auto_kb.cli status now reports mcp state. README now clarifies optional SDK fallback and upload boundary. Verified with two unit-test runs at 8/8 and full-auto-audit pass.

## Conclusion

当外部 Python SDK 无法安装时，AutoKnowledgeOS 应保持本地闭环和 MCP JSON-RPC fallback 可测试可用，同时在 status 和 README 中明确外部集成未激活；上传时只提交代码与 knowledge/，不提交 memory、vector、tasks 等本地运行态数据。
