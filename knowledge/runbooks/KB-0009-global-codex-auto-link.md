# KB-0009 Global Codex Auto-Link

- type: runbook
- status: published
- scope: personal-environment
- source_task: current
- tags: codex, global, mcp, auto-link, ascii-alias
- created_at: 2026-08-04T00:00:00
- published_at: 2026-08-04T00:00:00

## Conclusion

To make Codex auto-link to the central knowledge base across folders, use a personal global `C:\Users\hy\.codex\AGENTS.md` plus a global MCP server entry in `C:\Users\hy\.codex\config.toml`. Because Windows subprocesses can mangle Chinese paths, point automation at an ASCII junction alias such as `G:\AI_KB` that targets `G:\AI 架构`, while keeping the real data under `G:\AI 架构`.

## Practical Rule

- Global instruction lives in `C:\Users\hy\.codex\AGENTS.md`.
- MCP server launches with `python -m auto_kb.mcp_server`.
- Environment variables use `G:\AI_KB` for `AUTO_KB_ROOT` and `PYTHONPATH`.
- The alias keeps cross-computer startup reliable without moving the data off the G drive.

## Cross-Computer Update

When rebuilding the global Codex link on another computer, `tools\install-codex-global-link.ps1` must prefer `G:\AI_KB\.venv\Scripts\python.exe` if it exists. `换电脑初始化.bat` creates that project-local environment before installing the global link, so MCP dependencies travel with the G drive instead of relying on a random system Python.

