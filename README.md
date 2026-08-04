# AutoKnowledgeOS

Local-first knowledge closure for Codex.

AutoKnowledgeOS is a small local knowledge, memory, and task-closure system built to stop useful AI conversation results from disappearing in chat history. It keeps durable knowledge in Markdown, records task evidence locally, exposes knowledge actions through MCP, and verifies substantial work with a closure gate before calling it done.

## Why This Exists

When working with AI agents, the hard part is not only getting an answer. The hard part is keeping the reusable conclusions, decisions, preferences, pitfalls, and runbooks somewhere durable.

AutoKnowledgeOS treats knowledge closure as part of task completion:

- Search existing knowledge before substantial work.
- Create a task workspace with `goal.md`, `plan.md`, `preflight.md`, and `log.md`.
- Store evidence under the task's `evidence/` directory.
- Stage durable conclusions as candidate knowledge.
- Publish accepted knowledge to `knowledge/`.
- Run a gate before the final response.

## Core Features

- Authoritative Markdown knowledge base under `knowledge/`.
- Local SQLite state store under `memory/knowledge.db`.
- MCP tools for Codex: `kb.search`, `kb.stage`, `kb.publish`, `task.create`, `task.preflight`, `task.gate`, and `workflow.run`.
- Local fallback behavior when optional integrations are unavailable.
- Optional adapters for Mem0, Graphiti, Qdrant, and LangGraph.
- Windows one-click scripts for bootstrap, health check, workflow execution, and MCP startup.
- Global Codex bridge so Codex tasks opened in other folders can connect back to this central knowledge base.

## Repository Layout

```text
auto_kb/       Python package: CLI, store, workflow, adapters, MCP server
knowledge/     Authoritative Markdown knowledge
tools/         PowerShell automation scripts
hooks/         Utility hook scripts
gates/         Gate rule documents
workflows/     Workflow graph entrypoints
mcp-server/    MCP compatibility entrypoint
tests/         Unit tests
vector/        Vector configuration, not generated local indexes
portable/      Files for linking another folder to the central KB
```

Runtime state is intentionally local and ignored by Git:

```text
.venv/
.auto_kb/
memory/
tasks/
vector/qdrant_local/
.tmp-openai-docs-cache/
.env*
```

## Quick Start On Windows

From PowerShell:

```powershell
Set-Location -LiteralPath "G:\AI 架构"
powershell -ExecutionPolicy Bypass -File ".\一键知识库.ps1"
```

The menu provides:

1. Bootstrap / first-machine setup
2. Health check
3. Run a task closure workflow
4. Search the knowledge base
5. Start the MCP server

For a new computer or a moved drive, run:

```powershell
G:\AI 架构\换电脑初始化.bat
```

This creates or repairs the local virtual environment, initializes local state, creates the ASCII alias `G:\AI_KB`, and installs the global Codex bridge.

## Codex Global Bridge

The installer writes two global Codex settings:

- `C:\Users\<you>\.codex\AGENTS.md`
- `C:\Users\<you>\.codex\config.toml`

The MCP server is registered as `central_auto_kb` and points to:

```text
G:\AI_KB\.venv\Scripts\python.exe -m auto_kb.mcp_server
```

`G:\AI_KB` is a Windows junction alias for `G:\AI 架构`. The alias avoids subprocess encoding issues while the real files remain in the original project directory.

After installing the bridge, open a fresh Codex task in any folder and ask:

```text
先搜索中央知识库，再分析这个项目
```

or:

```text
搜索中央知识库：项目边界
```

## CLI Usage

```powershell
python -m auto_kb.cli init
python -m auto_kb.cli new-task "Example task" --goal "What must be achieved"
python -m auto_kb.cli preflight --task current --goal "What must be checked"
python -m auto_kb.cli evidence --task current --name proof.txt --content "Evidence"
python -m auto_kb.cli stage --summary "A durable conclusion" --type lesson --evidence "Why this is true"
python -m auto_kb.cli publish --id 1
python -m auto_kb.cli gate --task current
python -m auto_kb.cli search "project boundary"
python -m auto_kb.cli status
```

When running outside the repository, set:

```powershell
$env:AUTO_KB_ROOT = "G:\AI_KB"
$env:PYTHONPATH = "G:\AI_KB"
```

The CLI uses explicit `--root` first, then `AUTO_KB_ROOT`, then the current directory. The MCP server uses its configured root or `AUTO_KB_ROOT`, then the current directory.

## Verification

Run the unit tests:

```powershell
G:\AI_KB\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the full audit:

```powershell
powershell -ExecutionPolicy Bypass -File "G:\AI 架构\tools\full-auto-audit.ps1" -ProjectRoot "G:\AI 架构"
```

Current local verification:

- Unit tests: 9 passing tests.
- Full audit: `pass: true`.
- MCP mode: standard SDK when `mcp` is installed.
- Cross-directory CLI search: verified using `AUTO_KB_ROOT=G:\AI_KB`.
- Optional SDKs currently verified in the local `.venv`: `mem0`, `graphiti_core`, `qdrant_client`, `langgraph`, and `mcp`.

## Integration Model

| Layer | Role | Fallback |
|---|---|---|
| Markdown | Durable truth source | None; this is authoritative |
| SQLite | Local events, candidates, graph edges, memories, checkpoints | Built in |
| MCP | Codex tool surface | JSON-RPC fallback for tests/tools |
| Mem0 | Personal memory adapter | SQLite memory table |
| Graphiti | Temporal graph adapter | SQLite graph edge table |
| Qdrant | Local vector search adapter | Markdown keyword/SQLite index |
| LangGraph | Workflow/checkpoint adapter | Local checkpoint flow |

The current embedding helper is deterministic and local. Treat Markdown search as the reliable layer unless a real embedding model is configured.

## GitHub Publishing Boundary

Safe to publish after review:

- `auto_kb/`
- `knowledge/`
- `tools/`
- `hooks/`
- `gates/`
- `workflows/`
- `mcp-server/`
- `portable/`
- `tests/`
- `README.md`
- `AGENTS.md`
- `requirements.txt`

Do not publish local runtime state:

- `.venv/`
- `.env*`
- `.auto_kb/`
- `memory/`
- `tasks/`
- `vector/qdrant_local/`
- `.tmp-openai-docs-cache/`

Before pushing to a public repository, review `knowledge/` because it can contain personal preferences, local paths, and private decisions.

## 中文说明

AutoKnowledgeOS 是一个面向 Codex 的本地优先知识闭环系统。它的目标是把 AI 对话中形成的稳定经验、决策、偏好、踩坑记录和操作手册沉淀到 `knowledge/`，而不是只留在聊天记录里。

日常使用时，先运行 `G:\AI 架构\换电脑初始化.bat` 完成一次性配置；之后在任意项目文件夹中新开 Codex 任务，就可以通过全局 `central_auto_kb` MCP 连接中央知识库。

重要任务完成前，应满足：

- 有任务四件套：`goal.md`、`plan.md`、`preflight.md`、`log.md`
- 有可复查证据
- 稳定结论已进入 `knowledge/`
- `task.gate` 通过

## License

No license has been declared yet. Add a license before making the repository broadly reusable by others.
