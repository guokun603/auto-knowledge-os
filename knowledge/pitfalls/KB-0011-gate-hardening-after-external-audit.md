# KB-0011 Gate Hardening After External Audit

- type: lesson
- status: published
- scope: repository
- source_task: current
- tags: audit, gate, evidence, git, duplicate, workflow
- created_at: 2026-08-04T17:25:00
- published_at: 2026-08-04T17:25:00

## Evidence

Claude's external audit report identified that the system could pass with empty evidence, publish placeholder conclusions, duplicate knowledge files, claim unverified hook enforcement, and lacked Git history. Local verification confirmed the main issues.

## Conclusion

Passing a happy-path test is not enough for a knowledge-closure system. Gates must test adversarial cases: empty evidence, missing conclusions, duplicate publication, existing dirty runtime databases, invalid Git state, and unverified automation claims. After this audit, the project added stricter preflight behavior, non-empty evidence validation, no-conclusion workflow blocking, duplicate publish reuse, vector index de-duplication, Git initialization, safer global AGENTS backup behavior, repaired MCP startup, repaired gate documentation, and expanded tests from 5 to 8.
