$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $RepoRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3.11 -m venv $Venv
}

& $Python -m pip install --upgrade pip
Push-Location $RepoRoot
try {
    & $Python -m pip install -e ".[dev]"
}
finally {
    Pop-Location
}
Write-Host "Installed qwen-mcp development environment at $Venv"
