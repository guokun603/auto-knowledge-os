param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$ErrorActionPreference = "Stop"
python -m auto_kb.cli @Args
exit $LASTEXITCODE
