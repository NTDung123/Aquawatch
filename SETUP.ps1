param([switch]$CpuOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:YOLO_CONFIG_DIR = Join-Path $PSScriptRoot '.work'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.work\matplotlib'
New-Item -ItemType Directory -Force -Path '.work','models','data\videos','data\results' | Out-Null
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cần cài Python 3.12 64-bit từ python.org trước.' }
}
$UseCuda = (-not $CpuOnly) -and [bool](Get-Command nvidia-smi -ErrorAction SilentlyContinue)
$TorchIndex = if ($UseCuda) { 'https://download.pytorch.org/whl/cu126' } else { 'https://download.pytorch.org/whl/cpu' }
& '.\.venv\Scripts\python.exe' -m pip install --cache-dir .work\pip torch==2.7.1 torchvision==0.22.1 --index-url $TorchIndex
if ($LASTEXITCODE -ne 0) { throw 'Cài PyTorch thất bại. Có thể thử SETUP.ps1 -CpuOnly.' }
& '.\.venv\Scripts\python.exe' -m pip install --cache-dir .work\pip -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Cài dependency thất bại.' }
& '.\.venv\Scripts\python.exe' scripts\fetch_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Tải model/video thất bại. Xem docs/ASSETS.md.' }
Write-Host 'Sẵn sàng. Chạy .\RUN.ps1 rồi mở http://localhost:8000'
