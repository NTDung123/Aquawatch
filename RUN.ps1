param([int]$Port = 8000, [switch]$Lan)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:YOLO_CONFIG_DIR = Join-Path $PSScriptRoot '.work'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.work\matplotlib'
$BindAddress = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }
Write-Host "AquaWatch: http://localhost:$Port"
& '.\.venv\Scripts\python.exe' -m uvicorn aquawatch.api:app --host $BindAddress --port $Port
