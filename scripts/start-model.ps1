[CmdletBinding()]
param(
    [int]$ContextSize = 16384,
    [int]$Port = 8080,
    [int]$NCpuMoe = -1,
    [bool]$TuneIfMissing = $true,
    [switch]$Retune
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Model = "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M"
$TuningPath = Join-Path $RepoRoot ".local\qwen-tuning.json"

if ($Retune -and (Test-Path -LiteralPath $TuningPath)) {
    Remove-Item -LiteralPath $TuningPath -Force
}

if ($NCpuMoe -lt 0 -and -not (Test-Path -LiteralPath $TuningPath) -and $TuneIfMissing) {
    try {
        & (Join-Path $PSScriptRoot "tune-model.ps1") -Model $Model -OutputPath $TuningPath
    }
    catch {
        Write-Warning "Automatic n_cpu_moe tuning failed; falling back to --cpu-moe. $($_.Exception.Message)"
    }
}

if ($NCpuMoe -lt 0 -and (Test-Path -LiteralPath $TuningPath)) {
    $tuning = Get-Content -LiteralPath $TuningPath -Raw | ConvertFrom-Json
    $tuningModel = [string]$tuning.model
    if ($tuningModel -eq $Model) {
        $NCpuMoe = [int]$tuning.best_n_cpu_moe
    }
}

$CommonArgs = @(
    "-hf", $Model,
    "-c", "$ContextSize",
    "-ngl", "auto",
    "-fa", "on",
    "-ctk", "q8_0",
    "-ctv", "q8_0",
    "--jinja",
    "--host", "127.0.0.1",
    "--port", "$Port",
    "--alias", "qwen3-coder-30b-a3b"
)
if ($NCpuMoe -ge 0) {
    $CommonArgs += @("-ncmoe", "$NCpuMoe")
    Write-Host "Using tuned n_cpu_moe=$NCpuMoe"
}
else {
    $CommonArgs += "-cmoe"
    Write-Host "Using conservative --cpu-moe fallback"
}

if (Get-Command llama -ErrorAction SilentlyContinue) {
    & llama serve @CommonArgs
    exit $LASTEXITCODE
}

if (Get-Command llama-server -ErrorAction SilentlyContinue) {
    & llama-server @CommonArgs
    exit $LASTEXITCODE
}

throw "llama.cpp was not found on PATH. Install it first (for example: winget install llama.cpp)."
