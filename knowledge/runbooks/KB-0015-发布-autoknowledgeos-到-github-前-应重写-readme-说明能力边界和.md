# 发布 AutoKnowledgeOS 到 GitHub 前，应重写 README 说明能力边界和运行方法，并确保 .gitignore 排除 memory、tasks、.auto_kb、.venv、vector/qdrant_local、缓存和环境文件等本地运行态数据。

- id: 15
- type: runbook
- scope: repository
- status: published
- source_task: TASK-20260804-210606-发布-autoknowledgeos-到-github
- tags: github,readme,gitignore,publishing,privacy
- created_at: 2026-08-04T21:09:23
- published_at: 2026-08-04T21:09:33

## Evidence

2026-08-04: README 已重写；.gitignore 已补充 memory/、.auto_kb/ 等运行态目录；git status --ignored 显示运行态为 ignored；单元测试 9/9 通过。

## Conclusion

发布 AutoKnowledgeOS 到 GitHub 前，应重写 README 说明能力边界和运行方法，并确保 .gitignore 排除 memory、tasks、.auto_kb、.venv、vector/qdrant_local、缓存和环境文件等本地运行态数据。
