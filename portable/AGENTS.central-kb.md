# Central Knowledge Base Bridge

Use this file as `AGENTS.md` in any project folder that should connect to the central automated knowledge base.

## Central KB

- Central knowledge root: `{{CENTRAL_KB_ROOT}}`
- Before substantial work, use the central KB tools for preflight and knowledge retrieval.
- After substantial work, publish stable conclusions through the central KB tools.
- Do not create a separate disconnected knowledge base in this project unless the user explicitly requests it.

## Required Commands

Health check:

```powershell
powershell -ExecutionPolicy Bypass -File "{{CENTRAL_KB_ROOT}}\tools\health-check.ps1" -ProjectRoot "{{CENTRAL_KB_ROOT}}"
```

Run full workflow:

```powershell
powershell -ExecutionPolicy Bypass -File "{{CENTRAL_KB_ROOT}}\tools\run-workflow.ps1" -ProjectRoot "{{CENTRAL_KB_ROOT}}" -Title "任务名" -Goal "任务目标" -Conclusion "稳定结论"
```

Search knowledge:

```powershell
Set-Location -LiteralPath "{{CENTRAL_KB_ROOT}}"
python -m auto_kb.cli search "关键词"
```

## Completion Rule

Final response must mention the central KB updates under `{{CENTRAL_KB_ROOT}}\knowledge`, or say `KB-NOOP` with a reason.
