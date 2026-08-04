# User Collaboration Preferences

- type: preference
- status: accepted
- scope: global
- updated_at: 2026-08-04

## Preferences

### PREF-001 Stable conclusions must enter the knowledge system

The user requires stable conclusions, reusable lessons, decisions, durable constraints, reusable procedures, and collaboration preferences from conversation to be written into the relevant knowledge documents. They must not remain only in chat.

Evidence: user said all experience conclusions generated in chat must land in relevant knowledge base documents and must not remain only in the conversation.

### PREF-002 Do not downgrade the requested system

When the user asks for a complete automated system, do not replace it with a manual, simplified, beginner-only, or later-stage version. Build toward the requested complete target.

Evidence: user rejected the manual/minimal route and explicitly requested the automated version with vector database, LangGraph, Mem0, Graphiti, and MCP Server.

### PREF-003 Be decisive and execute

The user prefers Codex to make a clear engineering decision, implement it, test it, and report evidence, instead of repeatedly giving conceptual explanations.

Evidence: user said not to make excuses and asked Codex to decide how to complete the project.

### PREF-004 Keep knowledge data under G:\AI 架构

Knowledge data, task records, local state, vector data, and evidence should be stored under `G:\AI 架构`.

Evidence: user clarified that the data should be placed in `G:\AI 架构`.

## Storage Rules

- This file is the new authoritative preference file.
- Old preference files under `知识库/` are legacy copies and should not be used as the active source.
- Runtime preference memory is mirrored into `memory/knowledge.db` when published through the automation tools.
