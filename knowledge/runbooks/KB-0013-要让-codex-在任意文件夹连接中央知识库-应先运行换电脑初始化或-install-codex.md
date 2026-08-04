# 要让 Codex 在任意文件夹连接中央知识库，应先运行换电脑初始化或 install-codex-global-link.ps1，确保 G:\AI_KB 别名存在、全局 AGENTS.md 指向 G:\AI 架构、全局 config.toml 注册 central_auto_kb MCP，并重启或新开 Codex 任务加载配置。

- id: 13
- type: runbook
- scope: global
- status: published
- source_task: TASK-20260804-202645-说明任意目录连接中央知识库
- tags: codex,mcp,global-link,runbook,startup
- created_at: 2026-08-04T20:46:34
- published_at: 2026-08-04T20:47:23

## Evidence

2026-08-04: .venv dependencies installed; global config central_auto_kb points to G:\AI_KB\.venv\Scripts\python.exe; global AGENTS bridge installed; status and tests verified.

## Conclusion

要让 Codex 在任意文件夹连接中央知识库，应先运行换电脑初始化或 install-codex-global-link.ps1，确保 G:\AI_KB 别名存在、全局 AGENTS.md 指向 G:\AI 架构、全局 config.toml 注册 central_auto_kb MCP，并重启或新开 Codex 任务加载配置。

## Operator Steps

1. 首次或换电脑时运行 `G:\AI 架构\换电脑初始化.bat`。
2. 初始化后关闭旧的 Codex 任务，重新打开一个新任务，让全局 `C:\Users\guokun\.codex\config.toml` 和全局 `AGENTS.md` 生效。
3. 在任意项目文件夹中使用 Codex 时，先让 Codex 搜索中央知识库；优先使用 `central_auto_kb` MCP，MCP 不可用时回退到 `G:\AI 架构\knowledge` 文件和脚本。
4. 手工体检可运行 `G:\AI 架构\一键体检知识库.bat`，或运行 `powershell -ExecutionPolicy Bypass -File "G:\AI 架构\tools\health-check.ps1"`。
5. 项目内菜单可运行 `G:\AI 架构\一键启动知识库.bat`，其中包含初始化、体检、任务闭环、搜索知识库、启动 MCP 服务等入口。

## Current Machine Verification

2026-08-04: 当前机器已注册全局 `central_auto_kb` MCP；`AUTO_KB_ROOT` 和 `PYTHONPATH` 指向 `G:\AI_KB`；`G:\AI_KB` 是指向 `G:\AI 架构` 的英文路径别名；项目 `.venv` 中 `mem0`、`graphiti_core`、`qdrant_client`、`langgraph`、`mcp` 均可导入。要让任意目录的新 Codex 任务加载这个配置，关键动作是重启 Codex 或新开任务。
