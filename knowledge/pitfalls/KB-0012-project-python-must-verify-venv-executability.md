# KB-0012 Project Python Must Verify Venv Executability

- type: lesson
- status: published
- scope: repository
- source_task: current
- tags: python, venv, portability, bootstrap, audit
- created_at: 2026-08-05T08:26:00
- published_at: 2026-08-05T08:26:00

## Evidence

After the Preflight v2 update, `python -m unittest discover -s tests -v` passed with the system Python, but `tools/full-auto-audit.ps1` failed because it preferred `G:\AI 架构\.venv\Scripts\python.exe`. That copied virtual environment pointed to `C:\Users\guokun\AppData\Local\Programs\Python\Python312\python.exe`, which does not exist on the current computer.

## Conclusion

Cross-computer automation must not trust `.venv\Scripts\python.exe` merely because the file exists. The runner, bootstrap flow, and global Codex MCP installer must verify that the venv Python can actually run. If it cannot, the runner should fall back to a working system Python, and bootstrap with `-UseVenv` should back up the broken `.venv` and recreate it.
