param(
    [string]$Destination = 'D:\httm\data\research\MOBDrone_videos.zip'
)
$ErrorActionPreference = 'Stop'
$uri = 'https://zenodo.org/records/5996890/files/MOBDrone_videos.zip?download=1'
$parent = Split-Path -Parent $Destination
New-Item -ItemType Directory -Force -Path $parent | Out-Null
Write-Host 'Source: https://zenodo.org/records/5996890'
Write-Host 'Expected download: approximately 5.5 GB. This is a real dataset archive.'
Write-Host ('Destination: ' + $Destination)
& curl.exe -f -L --retry 5 --retry-delay 4 -C - -o $Destination $uri
if ($LASTEXITCODE -ne 0) {
    throw ('curl.exe failed with exit code ' + $LASTEXITCODE + '. You can rerun this command to resume.')
}
$hash = (Get-FileHash -Algorithm MD5 -LiteralPath $Destination).Hash.ToLowerInvariant()
$expected = '250c19fdd6fb0b5aa5fa43e5ad140306'
if ($hash -ne $expected) {
    throw ('MOBDrone MD5 mismatch. Actual: ' + $hash + '; expected: ' + $expected)
}
Write-Host 'MOBDrone archive verified against official Zenodo MD5.'
