# AutoKnowledgeOS

AutoKnowledgeOS is a local-first knowledge-closure framework for Codex. It turns reusable lessons from AI conversations into Markdown knowledge, then gives future Codex tasks a preflight and gate mechanism for consuming that knowledge before claiming completion.

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
5. It requires each action to be marked `resolved`, `needs-review`, or `rejected` before the completion gate passes.
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

Clone or download the repository, then place it where you want the central knowledge base to live. All examples below use `<project-root>` as a placeholder — substitute your actual repository path.

```text
<project-root>   e.g.  C:\auto-knowledge-os   or   G:\AI 架构
```

Run the first-machine setup:

```powershell
<project-root>\换电脑初始化.bat
```

The setup script creates or repairs:

- project `.venv`
- local SQLite state
- an ASCII junction alias (optional; avoids Windows subprocess encoding issues with non-ASCII paths)
- global Codex `AGENTS.md`
- global Codex MCP server config

If your project path contains non-ASCII characters (e.g. Chinese), the setup creates an ASCII-only junction alias so that subprocess calls don't mangle the path. If your path is already ASCII-only, the alias step is a no-op.

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

If MCP is unavailable, Codex should fall back to the files and scripts under `<project-root>`.

### Daily One-Click Menu

Run from the project directory:

```powershell
Set-Location -LiteralPath "<project-root>"
powershell -ExecutionPolicy Bypass -File ".\一键知识库.ps1"
```

Menu options:

1. Bootstrap / first-machine setup
2. Health check
3. Run a full task-closure workflow
4. Search the knowledge base
5. Start the MCP server

### Manual CLI Workflow

All CLI commands work from the project root. If calling from outside, set `AUTO_KB_ROOT`:

```powershell
$env:AUTO_KB_ROOT = "<project-root>"
$env:PYTHONPATH = "<project-root>"
```

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

The gate is the hard check inside this repository. Codex still needs to run the workflow or MCP tool; without a Codex lifecycle hook, this project cannot magically intercept every unrelated task by itself. The gate fails if:

- task quartet files are missing
- preflight is missing or invalid
- any `Required Actions` remain `pending`
- evidence is missing or empty
- candidate knowledge remains pending

### Search Knowledge

```powershell
python -m auto_kb.cli search "preflight"
```

From outside the repository:

```powershell
$env:AUTO_KB_ROOT = "<project-root>"
$env:PYTHONPATH = "<project-root>"
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

### Dry-Run Workflow (no filesystem writes)

Preview what preflight would flag without creating task directories or writing evidence:

```powershell
python -m auto_kb.cli workflow --title "test" --goal "test goal" --dry-run
```

The MCP `workflow.run` tool also accepts `dry_run: true`.

### Run Tests

```powershell
Set-Location -LiteralPath "<project-root>"
python -m unittest discover -s tests -v
```

If `.venv` was created on a different machine or user account, its `python.exe` is a
stub pointing at a base interpreter that no longer exists, and calling it directly
fails. The `tools\` scripts detect this and fall back to system Python; to rebuild
`.venv` itself, run `换电脑初始化.bat`.

Run the full audit:

```powershell
powershell -ExecutionPolicy Bypass -File "<project-root>\tools\full-auto-audit.ps1" -ProjectRoot "<project-root>"
```

Current verification:

- Unit tests: 35 passing tests (including external adapter smoke tests) on 2026-08-05.
- Full audit: `tools/full-auto-audit.ps1` writes `.auto_kb/full-auto-audit.json`; it passes only when the current task gate is closed or there is no active task.
- Cross-directory central knowledge search: verified through `central_auto_kb`.
- MCP server: `central_auto_kb`, with `mcp>=2.0,<3.0`.
- Qdrant: disabled by default because the local hash embedding fallback is not semantic; keyword search is the default (backed by SQLite FTS5 when available). Set `AUTO_KB_ENABLE_QDRANT=1` only for experiments.

### Repository Layout

```text
auto_kb/       Python package: CLI, store, workflow, adapters, MCP server
knowledge/     Authoritative Markdown knowledge
tools/         PowerShell automation scripts
hooks/         Utility hook scripts
gates/         Gate rule documents
workflows/     Workflow graph entrypoints
mcp-server/    MCP compatibility entrypoint
tests/         Unit tests (35 tests)
vector/        Vector configuration, not generated local indexes
portable/      Files for linking another folder to the central KB
.github/       CI workflows (GitHub Actions)
pyproject.toml Project metadata and packaging
LICENSE        MIT License
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

AutoKnowledgeOS 不是普通笔记目录。它是给 Codex 用的本地知识闭环框架：用 preflight 把旧知识变成当前任务约束，用 gate 验证任务能不能收尾。

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

> 以前知识库只是存东西。现在知识库会在任务前变成检查清单；只要走这个 workflow 或 MCP gate，没处理完就不能通过验收。

### 适合谁用

如果你希望 Codex：

- 记住你的项目经验
- 不靠聊天历史硬撑上下文
- 每次做事前先查旧坑
- 每次完成前留下证据
- 把稳定结论自动沉淀成 Markdown

那就适合用这个框架。注意：它能提供硬 gate 和一键脚本，但 Codex 本身如果没有生命周期 hook，仍需要通过 AGENTS/MCP/脚本触发这套流程。

### 第一次安装

把项目放到一个固定目录。以下示例用 `<project-root>` 代表你的实际路径（例如 `C:\auto-knowledge-os` 或 `G:\AI 架构`），请替换成你的真实路径：

```text
<project-root>
```

第一次使用，运行：

```powershell
<project-root>\换电脑初始化.bat
```

它会做这些事：

- 创建或修复 `.venv`
- 安装 Python 依赖
- 初始化本地数据库
- 如果项目路径含中文等非 ASCII 字符，创建 ASCII 英文路径别名
- 写入 Codex 全局 `AGENTS.md`
- 写入 Codex 全局 MCP 配置

如果你的路径本身是纯英文（如 `C:\auto-kb`），别名步骤会跳过，不影响使用。

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

按全局配置，Codex 应优先使用 MCP：

```text
central_auto_kb
```

如果 MCP 不可用，就退回直接读：

```text
<project-root>\knowledge
```

### 日常最简单用法

打开 PowerShell：

```powershell
Set-Location -LiteralPath "<project-root>"
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

从外部调用时先设环境变量：

```powershell
$env:AUTO_KB_ROOT = "<project-root>"
$env:PYTHONPATH = "<project-root>"
```

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

才算完成。这个 gate 是仓库内的硬检查；真正全自动取决于 Codex 是否按 AGENTS/MCP 调用它。

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
Set-Location -LiteralPath "<project-root>"
python -m unittest discover -s tests -v
```

如果 `.venv` 是在别的电脑或别的用户账号下创建的，里面的 `python.exe` 只是一个指向
已不存在的基础解释器的壳，直接调用会报 `No Python at ...`。`tools\` 下的脚本会检测
这种情况并回退到系统 Python；要重建 `.venv` 本身，运行 `换电脑初始化.bat`。

跑完整审计：

```powershell
powershell -ExecutionPolicy Bypass -File "<project-root>\tools\full-auto-audit.ps1" -ProjectRoot "<project-root>"
```

当前本机验证状态：

- 2026-08-05：单元测试 35 个通过（含外部适配器冒烟测试）。
- 完整体检会写入 `.auto_kb/full-auto-audit.json`；有当前任务时，必须先让当前任务 gate 通过。
- Qdrant 默认关闭，因为当前本地 hash embedding 不具备真实语义检索能力；默认使用关键词检索（SQLite FTS5 可用时优先使用全文检索）。

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
pyproject.toml
LICENSE
.github/
```

公开仓库推送前，要检查 `knowledge/`，因为里面可能有个人偏好、本机路径和私人决策。

## License

MIT — see [LICENSE](./LICENSE).
