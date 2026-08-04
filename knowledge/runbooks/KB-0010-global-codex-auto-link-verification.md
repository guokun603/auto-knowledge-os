# KB-0010 Global Codex Auto-Link Verification Must Parse Config And Launch MCP

- type: runbook
- status: published
- scope: personal-environment
- source_task: current
- tags: codex, global-config, mcp, verification, toml
- created_at: 2026-08-04T14:10:00
- published_at: 2026-08-04T14:10:00

## Conclusion

A global Codex knowledge-base auto-link is not verified merely because files exist. Verification must parse `C:\Users\hy\.codex\config.toml` as valid TOML, read the `mcp_servers.central_auto_kb` command, launch it from a folder outside `G:\AI 架构`, list MCP tools, and run `kb.search` against real central knowledge content.

## Evidence

On 2026-08-04, strict TOML parsing found an old malformed `[projects.'...']` entry in `C:\Users\hy\.codex\config.toml`. After removing that broken project block, `tomllib` parsed the config, `central_auto_kb` launched from `G:\知识库\零碎知识`, listed `kb.search`, `kb.stage`, `kb.publish`, `task.create`, `task.preflight`, `task.gate`, and `workflow.run`, and `kb.search` returned real Markdown entries from `G:\AI 架构\knowledge`.

## Rule

Future auto-link audits must include both static checks and end-to-end MCP checks. If `config.toml` cannot be parsed as TOML, fix the malformed block before claiming the global auto-link is complete.

## Fresh Task Window Verification

On 2026-08-04, a fresh Codex task was opened in `G:\知识库\零碎知识` instead of `G:\AI 架构`. The new task directly saw and called the `central_auto_kb` MCP server. `kb.search` with query `自动化` returned entries under `knowledge\pitfalls\...`, and the task verified those entries mapped to real files under `G:\AI 架构\knowledge` and were also reachable through `G:\AI_KB\knowledge`. This confirms the global auto-link works in a new non-central Codex task after configuration reload.
