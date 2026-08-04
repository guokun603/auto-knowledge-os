# AutoKnowledgeOS

> Local-first AI knowledge, memory, and task-closure system for Codex.

AutoKnowledgeOS is a local-first knowledge base designed to stop useful AI conversation results from disappearing in chat history. It gives Codex a central Markdown truth source, a local SQLite state store, MCP tools, task preflight, evidence capture, closure gates, and optional adapters for Qdrant, Mem0, Graphiti, and LangGraph.

## What It Does

- Keeps durable knowledge in `knowledge/` as Markdown files.
- Stores local runtime state in `memory/knowledge.db` with SQLite.
- Exposes MCP tools such as `kb.search`, `kb.stage`, `kb.publish`, `task.create`, `task.preflight`, `task.gate`, and `workflow.run`.
- Creates a task quartet for substantial work: `goal.md`, `plan.md`, `preflight.md`, and `log.md`.
- Requires non-empty evidence before a task can pass the closure gate.
- Blocks unresolved candidate knowledge instead of silently claiming completion.
- Reuses existing published knowledge when duplicate conclusions are detected.
- Supports local Qdrant storage at `vector/qdrant_local` when available.
- Uses local fallback behavior when Mem0, Graphiti, Qdrant, or LangGraph integrations are unavailable.
- Provides one-click Windows scripts for bootstrap, health checks, workflow runs, and MCP startup.

## Current Verification Status

Verified locally on Windows:

- Unit tests: 8 passing tests.
- Full audit: `tools/full-auto-audit.ps1` returns `pass: true`.
- Global Codex auto-link: a fresh Codex task outside this folder can call `central_auto_kb` and search this knowledge base.
- Git repository: the project is initialized as a Git repo; runtime databases, vector indexes, caches, virtual environments, and task evidence are ignored by `.gitignore`.

Important boundary: the hook scripts under `hooks/` are utility scripts. Do not treat them as verified automatic Codex lifecycle hooks unless the active Codex environment explicitly supports and runs them. The enforced path is CLI/MCP workflow plus `task.gate`.

## Storage Model

| Layer | Current mode | Local path |
|---|---|---|
| Markdown truth source | authoritative | `knowledge/` |
| SQLite | local state and fallback memory | `memory/knowledge.db` |
| Qdrant | local vector store when available | `vector/qdrant_local` |
| Mem0 | SDK available, local fallback used | SQLite memory table |
| Graphiti | SDK available, local fallback used | SQLite graph edge table |
| LangGraph | local StateGraph/checkpoint flow | SQLite checkpoints |

The current embedding helper is deterministic and local. Treat keyword search and Markdown truth as the reliable layer unless a real embedding model is configured.

## Quick Start

```powershell
Set-Location -LiteralPath "G:\AI 架构"
powershell -ExecutionPolicy Bypass -File ".\一键知识库.ps1"
```

Menu options:

1. Bootstrap / first-machine setup
2. Health check
3. Run a task closure workflow
4. Search the knowledge base
5. Start the MCP server

## Common Commands

```powershell
python -m auto_kb.cli init
python -m auto_kb.cli new-task "Example task"
python -m auto_kb.cli preflight --task current --goal "Task goal"
python -m auto_kb.cli evidence --task current --name proof.txt --content "proof"
python -m auto_kb.cli stage --summary "A durable conclusion" --type lesson --evidence "manual"
python -m auto_kb.cli publish --id 1
python -m auto_kb.cli gate --task current
python -m unittest discover -s tests -v
```

## Cross-Computer Setup

If this folder is on a removable G drive, run this once on a new computer:

```powershell
G:\AI 架构\换电脑初始化.bat
```

The bootstrap flow can create a project-local `.venv`, install dependencies, initialize the knowledge base, and reinstall the global Codex link. Automation may use `G:\AI_KB`, an ASCII junction alias pointing to `G:\AI 架构`, to avoid Windows subprocess encoding problems.

## Safety Notes Before Publishing

The repository includes `.gitignore` rules for local runtime data:

- `.venv/`
- `.env*`
- `memory/*.db`
- `vector/qdrant_local/`
- `.auto_kb/current_task`
- `.auto_kb/full-auto-audit.json`
- `tasks/`

Review `knowledge/` before pushing to a public GitHub repository, because it may contain personal preferences, local paths, and private decisions.

---

# AutoKnowledgeOS 中文说明

> 面向 Codex 的本地优先 AI 知识库、记忆系统和任务闭环系统。

AutoKnowledgeOS 的目标是：让 AI 对话里产生的稳定经验、偏好、决策和操作流程，不再只停留在聊天记录里，而是沉淀到可检索、可审计、可版本管理的 Markdown 知识库中。

## 主要功能

- `knowledge/` 保存权威 Markdown 知识。
- `memory/knowledge.db` 保存本地状态、候选知识、记忆、图关系和检查点。
- 通过 MCP 暴露 `kb.search`、`kb.stage`、`kb.publish`、`task.create`、`task.preflight`、`task.gate`、`workflow.run` 等工具。
- 重要任务会创建四件套：`goal.md`、`plan.md`、`preflight.md`、`log.md`。
- 结束前 gate 会检查是否有非空证据。
- 未处理的候选知识会阻止任务通过，不再把占位内容发布成正式知识。
- 发布知识前会做基础查重，避免同一句结论重复生成多个 KB 文件。
- Qdrant 可作为本地向量库，路径是 `vector/qdrant_local`。
- Mem0、Graphiti、LangGraph 可用时接入；不可用时使用 SQLite 本地兜底。
- 提供 Windows 一键脚本：初始化、体检、任务闭环、MCP 启动。

## 当前验证状态

本地已验证：

- 单元测试：8 个通过。
- 完整体检：`tools/full-auto-audit.ps1` 返回 `pass: true`。
- Codex 全局自动链接：新开的非本目录 Codex 任务可以直接调用 `central_auto_kb` 并搜索本知识库。
- Git 仓库：项目已初始化 Git；数据库、向量库、缓存、虚拟环境和任务证据已加入 `.gitignore`。

重要边界：`hooks/` 目录里的脚本目前只能视为工具脚本。除非当前 Codex 环境明确支持并实际执行这些 hooks，否则不要把它们宣传成已验证的自动生命周期门禁。当前已验证的强制路径是 CLI/MCP 工作流加 `task.gate`。

## 存储结构

| 层 | 当前模式 | 本地路径 |
|---|---|---|
| Markdown 真相源 | 权威知识 | `knowledge/` |
| SQLite | 本地状态和兜底记忆 | `memory/knowledge.db` |
| Qdrant | 可用时作为本地向量库 | `vector/qdrant_local` |
| Mem0 | SDK 已安装，当前走本地兜底 | SQLite memories 表 |
| Graphiti | SDK 已安装，当前走本地兜底 | SQLite graph_edges 表 |
| LangGraph | 本地流程和 checkpoint | SQLite checkpoints 表 |

当前 embedding 辅助函数是本地确定性实现，不等于真正语义模型。没有接入真实 embedding 模型前，以 Markdown 真相源和关键词检索作为可靠层。

## 快速启动

```powershell
Set-Location -LiteralPath "G:\AI 架构"
powershell -ExecutionPolicy Bypass -File ".\一键知识库.ps1"
```

菜单功能：

1. 换电脑/首次安装自检
2. 体检
3. 一键跑完整任务闭环
4. 搜索知识库
5. 启动 MCP 服务

## 常用命令

```powershell
python -m auto_kb.cli init
python -m auto_kb.cli new-task "示例任务"
python -m auto_kb.cli preflight --task current --goal "任务目标"
python -m auto_kb.cli evidence --task current --name proof.txt --content "证据"
python -m auto_kb.cli stage --summary "稳定结论" --type lesson --evidence "manual"
python -m auto_kb.cli publish --id 1
python -m auto_kb.cli gate --task current
python -m unittest discover -s tests -v
```

## 换电脑使用

如果这个项目在移动 G 盘上，新电脑第一次使用运行：

```powershell
G:\AI 架构\换电脑初始化.bat
```

初始化流程会尽量创建项目内 `.venv`、安装依赖、初始化知识库，并恢复 Codex 全局链接。自动化程序会优先使用 `G:\AI_KB` 这个英文路径别名，它指向真实目录 `G:\AI 架构`，用于规避 Windows 子进程中文路径乱码问题。

## 推送 GitHub 前注意

`.gitignore` 已经排除了：

- `.venv/`
- `.env*`
- `memory/*.db`
- `vector/qdrant_local/`
- `.auto_kb/current_task`
- `.auto_kb/full-auto-audit.json`
- `tasks/`

如果 GitHub 仓库是公开的，推送前必须检查 `knowledge/`，因为里面可能包含你的个人偏好、本地路径和私人决策。
