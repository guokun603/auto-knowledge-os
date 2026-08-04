# AutoKnowledgeOS 的 CLI 和 MCP 入口必须优先使用 AUTO_KB_ROOT 并切换到知识库根目录；只读搜索不应强制初始化 SQLite 写入，否则从非项目目录启动会失效。

- id: 14
- type: pitfall
- scope: repository
- status: published
- source_task: TASK-20260804-202645-说明任意目录连接中央知识库
- tags: codex,mcp,AUTO_KB_ROOT,sqlite,cross-directory
- created_at: 2026-08-04T20:56:41
- published_at: 2026-08-04T20:56:49

## Evidence

2026-08-04: 从 C:\Users\guokun 启动 auto_kb.cli search 曾因当前目录和 SQLite 写入状态失败；修复 cli/mcp_server 解析 AUTO_KB_ROOT 后 chdir(root)，并让 search 只读扫描 Markdown；9 个单元测试通过，跨目录搜索返回 KB-0013。

## Conclusion

AutoKnowledgeOS 的 CLI 和 MCP 入口必须优先使用 AUTO_KB_ROOT 并切换到知识库根目录；只读搜索不应强制初始化 SQLite 写入，否则从非项目目录启动会失效。
