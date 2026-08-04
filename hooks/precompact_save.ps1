$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path ".auto_kb" | Out-Null
python -m auto_kb.cli status | Out-File -FilePath ".auto_kb\precompact-status.json" -Encoding utf8
exit 0
