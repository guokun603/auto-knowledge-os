param([string]$Task = "current", [Parameter(Mandatory=$true)][string]$Goal)
$ErrorActionPreference = "Stop"
python -m auto_kb.cli preflight --task $Task --goal $Goal
exit $LASTEXITCODE
