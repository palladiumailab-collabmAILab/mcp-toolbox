param(
    [int]$ContextSize = 16384,
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$Model = "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M"
$CommonArgs = @(
    "-hf", $Model,
    "-c", "$ContextSize",
    "-cmoe",
    "-ngl", "auto",
    "-fa", "on",
    "-ctk", "q8_0",
    "-ctv", "q8_0",
    "--jinja",
    "--host", "127.0.0.1",
    "--port", "$Port",
    "--alias", "qwen3-coder-30b-a3b"
)

if (Get-Command llama -ErrorAction SilentlyContinue) {
    & llama serve @CommonArgs
    exit $LASTEXITCODE
}

if (Get-Command llama-server -ErrorAction SilentlyContinue) {
    & llama-server @CommonArgs
    exit $LASTEXITCODE
}

throw "llama.cpp was not found on PATH. Install it first (for example: winget install llama.cpp)."
