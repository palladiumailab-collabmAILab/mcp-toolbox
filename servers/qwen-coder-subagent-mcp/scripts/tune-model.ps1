[CmdletBinding()]
param(
    [int[]]$Candidates = @(48, 44, 40, 36, 32, 28, 24),
    [int]$PromptTokens = 128,
    [int]$GenerationTokens = 64,
    [int]$Repetitions = 2,
    [string]$Model = "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "llama-bench-common.ps1")

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $RepoRoot ".local\qwen-tuning.json"
}

$results = @()
foreach ($candidate in $Candidates) {
    Write-Host "Benchmarking n_cpu_moe=$candidate ..."
    try {
        $rows = @(Invoke-QwenLlamaBench `
            -NCpuMoe $candidate `
            -PromptTokens $PromptTokens `
            -GenerationTokens $GenerationTokens `
            -Repetitions $Repetitions `
            -Model $Model)
        $summary = Get-QwenBenchSummary `
            -Rows $rows `
            -NCpuMoe $candidate `
            -PromptTokens $PromptTokens `
            -GenerationTokens $GenerationTokens
        $results += $summary
        Write-Host ("  generation={0:N2} t/s, prompt={1:N2} t/s" -f `
            $summary.generation_tokens_per_second, $summary.prompt_tokens_per_second)
    }
    catch {
        Write-Warning "Skipping n_cpu_moe=${candidate}: $($_.Exception.Message)"
    }
}

if ($results.Count -eq 0) {
    throw "No n_cpu_moe candidate completed successfully."
}

$best = $results | Sort-Object generation_tokens_per_second -Descending | Select-Object -First 1
$payload = [ordered]@{
    schema_version = 1
    model = $Model
    best_n_cpu_moe = [int]$best.n_cpu_moe
    generation_tokens_per_second = [double]$best.generation_tokens_per_second
    prompt_tokens_per_second = [double]$best.prompt_tokens_per_second
    build_commit = [string]$best.build_commit
    build_number = [int]$best.build_number
    cpu_info = [string]$best.cpu_info
    gpu_info = [string]$best.gpu_info
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    candidates = $results
}

$directory = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($directory)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Selected n_cpu_moe=$($best.n_cpu_moe). Saved tuning to $OutputPath"
