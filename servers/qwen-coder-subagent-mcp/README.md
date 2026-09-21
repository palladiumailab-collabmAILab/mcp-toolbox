# Qwen Coder Subagent MCP

Codexからローカル `Qwen3-Coder-30B-A3B-Instruct Q4_K_M` を読み取り専用サブエージェントとして呼び出すためのMCPブリッジです。

## Architecture

```text
Codex
  -> stdio MCP: qwen-mcp
  -> persistent localhost HTTP
  -> llama.cpp
  -> Qwen3-Coder-30B-A3B-Instruct Q4_K_M
```

Qwenには任意shellや書込み権限を渡しません。MCPブリッジが許可する操作は、ファイル一覧・文字列検索・ファイル読取・`git status`・`git diff`だけです。変更、テスト実行、commit/push、最終判断は親Codexが担当します。

仕様正本: [`docs/specs/qwen-subagent.md`](docs/specs/qwen-subagent.md)

## Setup

Windows:

```powershell
winget install llama.cpp
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

`rg` (ripgrep) がPATHにあれば、Qwenのリポジトリ文字列検索は自動的に `rg` を使用します。ない場合はPython実装へフォールバックします。

## Start Qwen

`qwen_delegate` は明示的にallowlistされたGit worktreeの最上位だけを調査対象にします。既定値はdenyです。起動前に対象リポジトリを登録してください。

```powershell
$env:QWEN_ALLOWED_WORKSPACE_ROOTS = (Resolve-Path .).Path
```

複数リポジトリを許可する場合は、Windowsでは`;`、Unix系では`:`で絶対パスを区切ります。allowlistにないhome、兄弟リポジトリ、非Gitディレクトリは拒否されます。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-model.ps1
```

初回起動時は `llama-bench` で複数の `n_cpu_moe` 値を測定し、生成速度が最も高かった値を `.local/qwen-tuning.json` に保存して起動へ反映します。失敗した場合は安全側の `--cpu-moe` にフォールバックします。

GPU、llama.cpp、量子化を変更した後は再測定できます。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-model.ps1 -Retune
```

対象PC向け既定値:

- context: 16K
- MoE expert placement: `n_cpu_moe` 実測選択
- GPU layers: auto
- Flash Attention: on
- KV cache: Q8
- endpoint: `http://127.0.0.1:8080/v1`
- model alias: `qwen3-coder-30b-a3b`

## Codex / MCP

`.codex/config.toml` に `qwen-coder` MCPを登録済みです。Codexをこのリポジトリから起動すると以下を利用できます。

- `qwen_health`
- `qwen_delegate`

例:

```text
qwen_delegate を使ってこのrepoを読み取り専用でレビューし、
バグ候補を path:line の根拠付きで返して。変更はしないこと。
```

## Performance benchmark

性能計測はGPU・CPU・ドライバ・llama.cpp buildに依存するため、通常のGitHub Actionsには入れません。ローカルで基準値を作成します。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\benchmark-model.ps1 -WriteBaseline
```

その後の変更で:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\benchmark-model.ps1
```

prompt処理または生成速度が基準から既定15%以上低下すると失敗します。結果は `.local/` に保存され、Git管理しません。

実際のサブエージェント処理時間も含めて `n_cpu_moe` 候補を比較する場合は、[`docs/benchmark-subagent.md`](docs/benchmark-subagent.md) の固定タスク手順を使用します。実機測定で改善が確認されるまでは、起動時の自動選択規則は生成速度ベースのままです。

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `QWEN_BASE_URL` | `http://127.0.0.1:8080/v1` | llama.cpp API |
| `QWEN_MODEL` | `qwen3-coder-30b-a3b` | API model id |
| `QWEN_TIMEOUT_SECONDS` | `180` | HTTP timeout |
| `QWEN_MAX_ROUNDS` | `8` | local agent tool-loop limit |
| `QWEN_MAX_OUTPUT_TOKENS` | `2048` | one model response limit |
| `QWEN_MAX_TOOL_OUTPUT_CHARS` | `24000` | tool result cap |
| `QWEN_ALLOWED_WORKSPACE_ROOTS` | *(required)* | exact absolute paths of allowed top-level Git worktrees |

## Validation

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
docker build -t qwen-coder-subagent-mcp:test .
```

GitHub Actions runs deterministic quality gates only; hardware performance is measured separately with `benchmark-model.ps1`.
