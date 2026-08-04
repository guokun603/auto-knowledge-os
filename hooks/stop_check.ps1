$ErrorActionPreference = "Stop"
python -m auto_kb.cli gate --task current
exit $LASTEXITCODE
