# Windows bootstrap: virtualenv + deps, then hand off to the cross-platform setup.py.
# Works in both Windows PowerShell 5.1 (powershell.exe) and PowerShell 7+ (pwsh):
#   powershell -ExecutionPolicy Bypass -File labs\00-setup\bootstrap.ps1
#   pwsh       -ExecutionPolicy Bypass -File labs\00-setup\bootstrap.ps1
#
# Afterwards, use .\lab.ps1 <target> for every step GUIDE.md writes as `make <target>`.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found. Install 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "       Tick 'Add python.exe to PATH' in the installer." -ForegroundColor Yellow
    exit 1
}
$ver = & python -c "import sys;print('%d.%d' % sys.version_info[:2])"
$maj, $min = $ver -split '\.'
if ([int]$maj -lt 3 -or ([int]$maj -eq 3 -and [int]$min -lt 10)) {
    Write-Host "ERROR: Python $ver found, but this lab needs 3.10 or newer." -ForegroundColor Red
    exit 1
}
Write-Host "==> Python $ver"

if (-not (Test-Path '.venv')) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel | Out-Null
pip install -r requirements.txt

python .\labs\00-setup\setup.py

Write-Host ""
Write-Host "==> Next steps use .\lab.ps1 (the Windows equivalent of make):" -ForegroundColor Green
Write-Host "      .\lab.ps1            # list every target"
Write-Host "      .\lab.ps1 bench      # start track 01"
Write-Host "    Full walkthrough: GUIDE.md"
