# Preflight v2 已把知识闭环升级为风险消费闭环：命中的 pitfall 会生成 Required Actions，discussion 路由会进入 preflight，gate 会阻止 pending action 的任务完成，并提供 CLI/MCP resolve-action 来记录处理结果。

- id: 17
- type: lesson
- scope: repository
- status: published
- source_task: TASK-20260804-212659-升级-preflight-v2-高级知识闭环
- tags: preflight-v2,required-actions,gate,mcp,knowledge-consumption
- created_at: 2026-08-04T21:40:00
- published_at: 2026-08-04T21:41:30

## Evidence

2026-08-04: 修改 auto_kb/store.py、cli.py、mcp_server.py、workflow.py、tests/test_auto_kb.py、README.md、AGENTS.md 和 gates 文档；新增 gate blocks unresolved preflight actions 测试；单元测试 10/10 通过；当前任务 preflight 生成 RA-001..RA-010 并通过 resolve-action 标记 resolved。

## Conclusion

Preflight v2 已把知识闭环升级为风险消费闭环：命中的 pitfall 会生成 Required Actions，discussion 路由会进入 preflight，gate 会阻止 pending action 的任务完成，并提供 CLI/MCP resolve-action 来记录处理结果。
