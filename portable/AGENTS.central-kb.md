# Central Knowledge Base Bridge

Use this file as `AGENTS.md` in any project folder that should connect to the central automated knowledge base.

## Central KB

- Central knowledge root: `G:\AI 架构`
- Before substantial work, use the central KB tools for preflight and knowledge retrieval.
- After substantial work, publish stable conclusions through the central KB tools.
- Do not create a separate disconnected knowledge base in this project unless the user explicitly requests it.

## Required Commands

Health check:

```powershell
powershell -ExecutionPolicy Bypass -File "G:\AI 架构\tools\health-check.ps1" -ProjectRoot "G:\AI 架构"
```

Run full workflow:

```powershell
powershell -ExecutionPolicy Bypass -File "G:\AI 架构\tools\run-workflow.ps1" -ProjectRoot "G:\AI 架构" -Title "任务名" -Goal "任务目标" -Conclusion "稳定结论"
```

Search knowledge:

```powershell
Set-Location -LiteralPath "G:\AI 架构"
python -m auto_kb.cli search "关键词"
```

## Completion Rule

Final response must mention the central KB updates under `G:\AI 架构\knowledge`, or say `KB-NOOP` with a reason.
