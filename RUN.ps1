param([ValidateRange(1,65535)][int]$Port = 8000, [switch]$Lan)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:YOLO_CONFIG_DIR = Join-Path $PSScriptRoot '.work'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.work\matplotlib'
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Run .\SETUP.ps1 before starting AquaWatch.' }
& '.\.venv\Scripts\python.exe' -c "from aquawatch.settings import selected_model; model = selected_model(); print('Model:', model); raise SystemExit(0 if model.is_file() else 'Missing model. Run SETUP.ps1; see docs/INSTALL.md.')"
if ($LASTEXITCODE -ne 0) { throw 'AquaWatch model preflight failed. See the error above.' }
$BindAddress = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }
Write-Host "AquaWatch: http://localhost:$Port"
& '.\.venv\Scripts\python.exe' -m uvicorn aquawatch.api:app --host $BindAddress --port $Port
if ($LASTEXITCODE -ne 0) { throw 'AquaWatch stopped with an error. Check the port and the server output above.' }
