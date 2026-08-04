param([Parameter(Mandatory=$true)][string]$Title, [string]$Goal = "")
$ErrorActionPreference = "Stop"
if ($Goal) { python -m auto_kb.cli new-task $Title --goal $Goal } else { python -m auto_kb.cli new-task $Title }
exit $LASTEXITCODE
