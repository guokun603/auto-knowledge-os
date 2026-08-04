param([string]$Task = "current")
$ErrorActionPreference = "Stop"
python -m auto_kb.cli gate --task $Task
exit $LASTEXITCODE
