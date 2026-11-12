param([switch]$CpuOnly, [switch]$Baseline, [switch]$SampleVideos)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:YOLO_CONFIG_DIR = Join-Path $PSScriptRoot '.work'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.work\matplotlib'
New-Item -ItemType Directory -Force -Path '.work','models','data\videos','data\results' | Out-Null
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    $PythonCommand = $null
    $PythonArguments = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3.12 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32 else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { $PythonCommand = 'py'; $PythonArguments = @('-3.12') }
        } catch { }
    }
    if (-not $PythonCommand -and (Get-Command python -ErrorAction SilentlyContinue)) {
        try {
            & python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32 else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { $PythonCommand = 'python' }
        } catch { }
    }
    if (-not $PythonCommand) { throw 'Install Python 3.12 64-bit from python.org (include Python Launcher or add python to PATH).' }
    & $PythonCommand @PythonArguments -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Check Python 3.12 and write permission in this folder.' }
}
& '.\.venv\Scripts\python.exe' -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32 else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Existing .venv must use Python 3.12 64-bit. Rename the old .venv, then run SETUP.ps1 again.' }
$UseCuda = $false
if (-not $CpuOnly -and (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    try {
        & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Out-Null
        $UseCuda = $LASTEXITCODE -eq 0
    } catch { $UseCuda = $false }
}
$TorchIndex = if ($UseCuda) { 'https://download.pytorch.org/whl/cu126' } else { 'https://download.pytorch.org/whl/cpu' }
Write-Host "Installing PyTorch from $TorchIndex"
$InstalledTorch = & '.\.venv\Scripts\python.exe' -c "import importlib.metadata as m; print(m.version('torch') if 'torch' in {d.metadata['Name'].lower() for d in m.distributions()} else '')"
$TorchArguments = @('-m','pip','install','--cache-dir','.work\pip','torch==2.7.1','torchvision==0.22.1','--index-url',$TorchIndex)
if (($UseCuda -and $InstalledTorch -notlike '*+cu126') -or (-not $UseCuda -and $InstalledTorch -notlike '*+cpu')) {
    $TorchArguments += '--force-reinstall'
}
& '.\.venv\Scripts\python.exe' @TorchArguments
if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed. Retry SETUP.ps1 -CpuOnly if CUDA is unavailable.' }
& '.\.venv\Scripts\python.exe' -m pip install --cache-dir .work\pip -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check network access and docs/INSTALL.md.' }
& '.\.venv\Scripts\python.exe' -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Installed dependencies conflict. See pip check output above.' }
& '.\.venv\Scripts\python.exe' -c "import torch; print('PyTorch:', torch.__version__, '| CUDA available:', torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0) { throw 'PyTorch could not load. Install the Microsoft Visual C++ x64 Redistributable or retry SETUP.ps1 -CpuOnly; see docs/INSTALL.md.' }
if ($UseCuda) {
    & '.\.venv\Scripts\python.exe' -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'CUDA wheel installed but GPU is unavailable. Update the NVIDIA driver or retry SETUP.ps1 -CpuOnly.' }
}
$AssetArguments = @('scripts\fetch_assets.py')
if ($Baseline) { $AssetArguments += '--baseline' }
& '.\.venv\Scripts\python.exe' @AssetArguments
if ($LASTEXITCODE -ne 0) { throw 'Model verification failed. See the error above and docs/INSTALL.md.' }
if ($SampleVideos) {
    & '.\.venv\Scripts\python.exe' scripts\fetch_cctv_library.py --activate
    if ($LASTEXITCODE -ne 0) { throw 'Optional CCTV library setup failed. The model is ready; retry the sample download or upload your own pool video.' }
}
Write-Host 'Ready. Run .\RUN.ps1 then open http://localhost:8000'
