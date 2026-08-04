# Automated Knowledge Closure Rules

## Non-Negotiable Goal

This repository is an automated knowledge-closure system. Codex must treat knowledge closure as part of task completion.

## Required Automation Flow

For any substantial task:

1. Create or identify a task workspace under `tasks/`.
2. Maintain the task quartet: `goal.md`, `plan.md`, `preflight.md`, `log.md`.
3. Run or simulate the knowledge preflight before execution.
4. Store evidence under the task `evidence/` directory.
5. Treat Preflight v2 `Required Actions` as task-local obligations; each must be marked `resolved`, `needs-review`, or `rejected`.
6. Extract durable conclusions as candidate knowledge.
7. Publish accepted or verified knowledge to `knowledge/` Markdown files.
8. Update derived memory/index layers through automation tools.
9. Run the gate before final response.

## Knowledge Architecture

- `knowledge/` is the authoritative source of truth.
- `memory/knowledge.db` stores events, candidates, checkpoints, fallback memories, graph edges, and vector documents.
- Mem0 is the personal preference memory layer when available; local SQLite fallback is mandatory.
- Graphiti is the temporal knowledge graph layer when available; local SQLite fallback is mandatory.
- Qdrant is the vector retrieval layer when available; local SQLite fallback is mandatory.
- LangGraph is the workflow/checkpoint layer when available; local graph fallback is mandatory.
- MCP Server exposes knowledge and task actions to Codex.

## Completion Gate

A task is not complete unless the task quartet exists, preflight contains a gate result, every Preflight v2 required action is closed as `resolved`, `needs-review`, or `rejected`, evidence exists, and no candidate knowledge remains pending for this task unless marked `needs-review` or `rejected`.

## Do Not

- Do not rely on chat history as the authoritative knowledge store.
- Do not load all historical conversations into context.
- Do not treat knowledge search hits as consumed until they become required actions and receive a closure status.
- Do not publish uncertain guesses as facts.
- Do not claim completion when the gate fails.
