Set-StrictMode -Version Latest

$script:QwenDefaultModel = "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M"

function Get-LlamaBenchCommand {
    foreach ($name in @("llama-bench", "llama-bench.exe")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }
    throw "llama-bench was not found on PATH. Install a recent llama.cpp build first."
}

function Invoke-QwenLlamaBench {
    param(
        [Parameter(Mandatory = $true)]
        [int]$NCpuMoe,
        [int]$PromptTokens = 128,
        [int]$GenerationTokens = 64,
        [int]$Repetitions = 2,
        [string]$Model = $script:QwenDefaultModel
    )

    $bench = Get-LlamaBenchCommand
    $arguments = @(
        "-hf", $Model,
        "-p", "$PromptTokens",
        "-n", "$GenerationTokens",
        "-r", "$Repetitions",
        "-o", "json",
        "-ngl", "999",
        "-ncmoe", "$NCpuMoe",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0"
    )

    $stderrFile = [System.IO.Path]::GetTempFileName()
    try {
        $stdout = & $bench @arguments 2> $stderrFile
        $exitCode = $LASTEXITCODE
        $stderr = Get-Content -LiteralPath $stderrFile -Raw -ErrorAction SilentlyContinue
    }
    finally {
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }

    if ($exitCode -ne 0) {
        throw "llama-bench failed for n_cpu_moe=$NCpuMoe (exit $exitCode).`n$stderr"
    }

    $json = ($stdout -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($json)) {
        throw "llama-bench returned no JSON output for n_cpu_moe=$NCpuMoe."
    }
    return @($json | ConvertFrom-Json)
}

function Get-QwenBenchSummary {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Rows,
        [Parameter(Mandatory = $true)]
        [int]$NCpuMoe,
        [int]$PromptTokens = 128,
        [int]$GenerationTokens = 64
    )

    $prompt = $Rows | Where-Object {
        [int]$_.n_prompt -eq $PromptTokens -and [int]$_.n_gen -eq 0
    } | Select-Object -First 1
    $generation = $Rows | Where-Object {
        [int]$_.n_prompt -eq 0 -and [int]$_.n_gen -eq $GenerationTokens
    } | Select-Object -First 1

    if ($null -eq $prompt -or $null -eq $generation) {
        throw "llama-bench JSON did not contain the expected prompt/generation rows."
    }

    return [pscustomobject][ordered]@{
        n_cpu_moe = $NCpuMoe
        prompt_tokens_per_second = [double]$prompt.avg_ts
        generation_tokens_per_second = [double]$generation.avg_ts
        build_commit = [string]$generation.build_commit
        build_number = [int]$generation.build_number
        cpu_info = [string]$generation.cpu_info
        gpu_info = [string]$generation.gpu_info
        backend = [string]$generation.backends
    }
}
