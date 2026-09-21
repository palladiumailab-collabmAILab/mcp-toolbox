$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    [Console]::Error.WriteLine("qwen-mcp venv not found. Run scripts/setup.ps1 first.")
    exit 1
}

Set-Location $RepoRoot
& $Python -m qwen_mcp.server
exit $LASTEXITCODE
