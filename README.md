# AutoKnowledgeOS

AutoKnowledgeOS is a local-first knowledge-closure framework for Codex. It turns reusable lessons from AI conversations into Markdown knowledge, then makes future Codex tasks consume that knowledge before claiming completion.

The short version:

```text
old knowledge -> preflight required actions -> evidence -> gate -> published knowledge
```

## English Guide

### What This Framework Does

AutoKnowledgeOS is not only a note folder. It is a task discipline system for AI agents:

1. It stores durable knowledge in `knowledge/`.
2. It creates a task workspace under `tasks/`.
3. It runs `preflight` before substantial work.
4. It converts matched pitfalls into `Required Actions`.
5. It forces each action to be marked `resolved`, `needs-review`, or `rejected`.
6. It requires evidence before completion.
7. It publishes stable conclusions back to `knowledge/`.
8. It exposes the workflow to Codex through MCP.

### Who Should Use It

Use this framework if you want Codex to remember project lessons without loading long chat history, and if you want every substantial task to finish with reviewable evidence instead of a vague "done".

It is especially useful for:

- personal AI knowledge bases
- reusable project runbooks
- Codex task discipline
- local memory and retrieval experiments
- agent workflow governance

### Install On Windows

Clone or download the repository, then place it where you want the central knowledge base to live.

This project was designed around a Windows path like:

```text
G:\AI 架构
```

Run the first-machine setup:

```powershell
G:\AI 架构\换电脑初始化.bat
```

The setup script creates or repairs:

- project `.venv`
- local SQLite state
- `G:\AI_KB` ASCII junction alias
- global Codex `AGENTS.md`
- global Codex MCP server config

`G:\AI_KB` points to `G:\AI 架构`. The alias avoids Windows subprocess encoding problems.

### Connect Codex From Any Folder

After setup, open a fresh Codex task in any project folder and say:

```text
Search the central knowledge base first, then analyze this project.
```

or in Chinese:

```text
先搜索中央知识库，再分析这个项目。
```

Codex should use the global MCP server named:

```text
central_auto_kb
```

If MCP is unavailable, Codex should fall back to the files and scripts under `G:\AI 架构`.

### Daily One-Click Menu

Run:

```powershell
Set-Location -LiteralPath "G:\AI 架构"
powershell -ExecutionPolicy Bypass -File ".\一键知识库.ps1"
```

Menu options:

1. Bootstrap / first-machine setup
2. Health check
3. Run a full task-closure workflow
4. Search the knowledge base
5. Start the MCP server

### Manual CLI Workflow

Create a task:

```powershell
python -m auto_kb.cli new-task "Improve README" --goal "Explain how users should run AutoKnowledgeOS"
```

Run preflight:

```powershell
python -m auto_kb.cli preflight --task current --goal "Explain usage clearly"
```

Preflight v2 writes `Required Actions` into `tasks/<task>/preflight.md`. Example:

```text
- [pending] RA-001 (pitfall) knowledge\pitfalls\PIT-001-no-evidence-no-completion.md :: Review and handle...
```

Resolve required actions:

```powershell
python -m auto_kb.cli resolve-action --task current --id RA-001 --status resolved --note "Added evidence check"
python -m auto_kb.cli resolve-action --task current --id all --status needs-review --note "Reviewed and intentionally deferred"
```

Add evidence:

```powershell
python -m auto_kb.cli evidence --task current --name proof.txt --content "Tests passed and README updated"
```

Stage and publish durable knowledge:

```powershell
python -m auto_kb.cli stage --summary "Preflight required actions must be closed before completion" --type lesson --evidence "Implemented and tested"
python -m auto_kb.cli publish --id 1
```

Run the completion gate:

```powershell
python -m auto_kb.cli gate --task current
```

The gate fails if:

- task quartet files are missing
- preflight is missing or invalid
- any `Required Actions` remain `pending`
- evidence is missing or empty
- candidate knowledge remains unpublished

### Search Knowledge

```powershell
python -m auto_kb.cli search "preflight"
```

From outside the repository:

```powershell
$env:AUTO_KB_ROOT = "G:\AI_KB"
$env:PYTHONPATH = "G:\AI_KB"
python -m auto_kb.cli search "project boundary"
```

### Check System Status

Fast status check:

```powershell
python -m auto_kb.cli status
```

Deep adapter initialization:

```powershell
python -m auto_kb.cli status --deep
```

Use `status` for normal health checks. Use `status --deep` only when you explicitly want to initialize optional SDK clients.

### Run Tests

```powershell
G:\AI_KB\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the full audit:

```powershell
powershell -ExecutionPolicy Bypass -File "G:\AI 架构\tools\full-auto-audit.ps1" -ProjectRoot "G:\AI 架构"
```

Current verification:

- Unit tests: 10 passing tests.
- Full audit: `pass: true`.
- Cross-directory central knowledge search: verified.
- MCP server: `central_auto_kb`.
- Optional package probe: `mem0`, `graphiti_core`, `qdrant_client`, `langgraph`, `mcp`.

### Repository Layout

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

### What Not To Upload

The project is local-first. These paths are local runtime state and are ignored by Git:

```text
.venv/
.auto_kb/
memory/
tasks/
vector/qdrant_local/
.tmp-openai-docs-cache/
.env*
```

Review `knowledge/` before publishing to a public repository, because knowledge files may contain personal preferences, local paths, and private decisions.

## 中文指南

### 这个框架是干什么的

AutoKnowledgeOS 不是普通笔记目录。它是给 Codex 用的本地知识闭环框架。

它解决的问题是：

```text
AI 对话里形成的经验，不能只留在聊天记录里。
下一次做任务时，旧经验必须重新生效。
```

它的核心流程是：

```text
旧知识
-> 任务前 preflight
-> 命中隐患
-> 生成 Required Actions
-> 逐条处理
-> 写证据
-> gate 验收
-> 新结论再写回 knowledge
```

人话版：

> 以前知识库只是存东西。现在知识库会在每次任务前变成检查清单，没处理完不让说完成。

### 适合谁用

如果你希望 Codex：

- 记住你的项目经验
- 不靠聊天历史硬撑上下文
- 每次做事前先查旧坑
- 每次完成前留下证据
- 把稳定结论自动沉淀成 Markdown

那就适合用这个框架。

### 第一次安装

把项目放到一个固定目录，例如：

```text
G:\AI 架构
```

第一次使用，运行：

```powershell
G:\AI 架构\换电脑初始化.bat
```

它会做这些事：

- 创建或修复 `.venv`
- 安装 Python 依赖
- 初始化本地数据库
- 创建 `G:\AI_KB` 英文路径别名
- 写入 Codex 全局 `AGENTS.md`
- 写入 Codex 全局 MCP 配置

`G:\AI_KB` 指向真实目录 `G:\AI 架构`，主要是为了避免 Windows 中文路径在子进程里乱码。

### 让 Codex 在任意文件夹连接知识库

安装完成后，重新打开一个 Codex 新任务。

你可以在任意项目文件夹里说：

```text
先搜索中央知识库，再分析这个项目。
```

或者：

```text
搜索中央知识库：项目边界
```

Codex 会优先使用 MCP：

```text
central_auto_kb
```

如果 MCP 不可用，就退回直接读：

```text
G:\AI 架构\knowledge
```

### 日常最简单用法

打开 PowerShell：

```powershell
Set-Location -LiteralPath "G:\AI 架构"
powershell -ExecutionPolicy Bypass -File ".\一键知识库.ps1"
```

菜单里有：

1. 换电脑/首次安装
2. 体检
3. 跑完整任务闭环
4. 搜索知识库
5. 启动 MCP 服务

新手优先用这个菜单。

### 手动跑一次完整任务

创建任务：

```powershell
python -m auto_kb.cli new-task "改 README" --goal "让用户看懂怎么使用这个框架"
```

任务目录会生成：

```text
tasks/<任务ID>/goal.md
tasks/<任务ID>/plan.md
tasks/<任务ID>/preflight.md
tasks/<任务ID>/log.md
tasks/<任务ID>/evidence/
```

运行 preflight：

```powershell
python -m auto_kb.cli preflight --task current --goal "让用户看懂怎么使用这个框架"
```

如果命中旧隐患，`preflight.md` 会出现：

```text
## Required Actions
- [pending] RA-001 ...
- [pending] RA-002 ...
```

这表示旧知识已经被消费成当前任务的待办项。

处理待办项：

```powershell
python -m auto_kb.cli resolve-action --task current --id RA-001 --status resolved --note "已经在 README 中补充使用步骤"
```

如果全部都已经看过，可以批量标记：

```powershell
python -m auto_kb.cli resolve-action --task current --id all --status resolved --note "已逐项检查并处理"
```

可用状态有三个：

```text
resolved      已处理
needs-review 需要人工复查
rejected      不适用或拒绝
```

写证据：

```powershell
python -m auto_kb.cli evidence --task current --name proof.txt --content "README 已更新，测试已通过"
```

沉淀稳定结论：

```powershell
python -m auto_kb.cli stage --summary "README 必须同时提供中文和英文使用说明" --type lesson --evidence "本次发布要求"
python -m auto_kb.cli publish --id 1
```

最后验收：

```powershell
python -m auto_kb.cli gate --task current
```

如果返回：

```json
{"pass": true}
```

才算完成。

### 为什么 Preflight v2 更高级

旧版只是：

```text
我搜到了这些相关知识。
```

新版是：

```text
我搜到了这些旧坑。
我把它们变成当前任务必须处理的 RA-001、RA-002。
你没处理完，我就不让任务通过 gate。
```

所以它不是单纯记忆系统，而是任务治理系统。

### 检查项目是否正常

快速体检：

```powershell
python -m auto_kb.cli status
```

深度检查外部适配器：

```powershell
python -m auto_kb.cli status --deep
```

跑单元测试：

```powershell
G:\AI_KB\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

跑完整审计：

```powershell
powershell -ExecutionPolicy Bypass -File "G:\AI 架构\tools\full-auto-audit.ps1" -ProjectRoot "G:\AI 架构"
```

### 哪些文件不要上传

这些是本地运行状态，不要传 GitHub：

```text
.venv/
.auto_kb/
memory/
tasks/
vector/qdrant_local/
.tmp-openai-docs-cache/
.env*
```

可以上传的主要是：

```text
auto_kb/
knowledge/
tools/
hooks/
gates/
workflows/
mcp-server/
portable/
tests/
README.md
AGENTS.md
requirements.txt
```

公开仓库推送前，要检查 `knowledge/`，因为里面可能有个人偏好、本机路径和私人决策。

## License

No license has been declared yet. Add a license before making the repository broadly reusable by others.
