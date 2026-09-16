[CmdletBinding()]
param(
    [int]$NCpuMoe = -1,
    [int]$PromptTokens = 512,
    [int]$GenerationTokens = 128,
    [int]$Repetitions = 3,
    [double]$MaxRegressionPercent = 15.0,
    [switch]$WriteBaseline,
    [string]$BaselinePath = "",
    [string]$OutputPath = "",
    [string]$Model = "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "llama-bench-common.ps1")

if ([string]::IsNullOrWhiteSpace($BaselinePath)) {
    $BaselinePath = Join-Path $RepoRoot ".local\qwen-benchmark-baseline.json"
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $RepoRoot ".local\qwen-benchmark-latest.json"
}
if ($NCpuMoe -lt 0) {
    $tuningPath = Join-Path $RepoRoot ".local\qwen-tuning.json"
    if (-not (Test-Path -LiteralPath $tuningPath)) {
        throw "No tuning result found. Run scripts/tune-model.ps1 first or pass -NCpuMoe."
    }
    $tuning = Get-Content -LiteralPath $tuningPath -Raw | ConvertFrom-Json
    $NCpuMoe = [int]$tuning.best_n_cpu_moe
}

$rows = @(Invoke-QwenLlamaBench `
    -NCpuMoe $NCpuMoe `
    -PromptTokens $PromptTokens `
    -GenerationTokens $GenerationTokens `
    -Repetitions $Repetitions `
    -Model $Model)
$summary = Get-QwenBenchSummary `
    -Rows $rows `
    -NCpuMoe $NCpuMoe `
    -PromptTokens $PromptTokens `
    -GenerationTokens $GenerationTokens

$result = [ordered]@{
    schema_version = 1
    model = $Model
    n_cpu_moe = $NCpuMoe
    prompt_tokens = $PromptTokens
    generation_tokens = $GenerationTokens
    repetitions = $Repetitions
    prompt_tokens_per_second = [double]$summary.prompt_tokens_per_second
    generation_tokens_per_second = [double]$summary.generation_tokens_per_second
    build_commit = [string]$summary.build_commit
    build_number = [int]$summary.build_number
    cpu_info = [string]$summary.cpu_info
    gpu_info = [string]$summary.gpu_info
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
}

$outputDirectory = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host ("Current: generation={0:N2} t/s, prompt={1:N2} t/s" -f `
    $result.generation_tokens_per_second, $result.prompt_tokens_per_second)

if ($WriteBaseline) {
    $baselineDirectory = Split-Path -Parent $BaselinePath
    if (-not [string]::IsNullOrWhiteSpace($baselineDirectory)) {
        New-Item -ItemType Directory -Path $baselineDirectory -Force | Out-Null
    }
    $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $BaselinePath -Encoding utf8
    Write-Host "Baseline written to $BaselinePath"
    exit 0
}

if (-not (Test-Path -LiteralPath $BaselinePath)) {
    Write-Warning "No baseline exists at $BaselinePath. Use -WriteBaseline to create one."
    exit 0
}

$baseline = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json
$ratio = 1.0 - ($MaxRegressionPercent / 100.0)
$generationFloor = [double]$baseline.generation_tokens_per_second * $ratio
$promptFloor = [double]$baseline.prompt_tokens_per_second * $ratio
$regressions = @()
if ($result.generation_tokens_per_second -lt $generationFloor) {
    $regressions += "generation"
}
if ($result.prompt_tokens_per_second -lt $promptFloor) {
    $regressions += "prompt"
}

if ($regressions.Count -gt 0) {
    throw "Performance regression exceeded $MaxRegressionPercent% for: $($regressions -join ', ')."
}
Write-Host "Performance is within the allowed regression threshold ($MaxRegressionPercent%)."
