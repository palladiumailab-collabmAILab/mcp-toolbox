# foo — Qwen coding subagent MCP

Codexからローカル `Qwen3-Coder-30B-A3B-Instruct Q4_K_M` を読み取り専用サブエージェントとして呼び出すためのMCPブリッジです。

## Architecture

```text
Codex
  -> stdio MCP: qwen-mcp
  -> llama.cpp OpenAI-compatible API
  -> Qwen3-Coder-30B-A3B-Instruct Q4_K_M
```

Qwenには任意shellや書込み権限を渡しません。MCPブリッジが許可する操作は、ファイル一覧・文字列検索・ファイル読取・`git status`・`git diff`だけです。変更、テスト実行、commit/push、最終判断は親Codexが担当します。

仕様正本: [`docs/specs/qwen-subagent.md`](docs/specs/qwen-subagent.md)

## 1. llama.cpp をインストール

Windows:

```powershell
winget install llama.cpp
```

## 2. Python環境を作る

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

## 3. Qwenを起動

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-model.ps1
```

初回は `lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M` を取得します。Q4_K_Mは約18.6GBです。

対象PC（RTX 4060 8GB / RAM 32GB）向けの初期設定:

- context: 16K
- MoE experts: CPU
- GPU layers: auto
- Flash Attention: on
- KV cache: Q8
- endpoint: `http://127.0.0.1:8080/v1`
- model alias: `qwen3-coder-30b-a3b`

## 4. MCP単体確認

別ターミナルで:

```powershell
.\.venv\Scripts\python.exe -m qwen_mcp.server
```

stdio MCPなので、正常時は何も表示せず入力待ちになります。開発確認にはMCP Inspectorも使えます。

```powershell
.\.venv\Scripts\mcp.exe dev src\qwen_mcp\server.py
```

## 5. Codexから使う

`.codex/config.toml` に `qwen-coder` MCPを登録済みです。Codexをこのリポジトリから起動し直すと、次のMCP toolsを利用できます。

- `qwen_health`
- `qwen_delegate`

例:

```text
qwen_delegate を使ってこのrepoのMCP実装を読み取り専用でレビューし、
バグ候補を path:line の根拠付きで返して。変更はしないこと。
```

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `QWEN_BASE_URL` | `http://127.0.0.1:8080/v1` | llama.cpp API |
| `QWEN_MODEL` | `qwen3-coder-30b-a3b` | API model id |
| `QWEN_TIMEOUT_SECONDS` | `180` | HTTP timeout |
| `QWEN_MAX_ROUNDS` | `8` | local agent tool-loop limit |
| `QWEN_MAX_OUTPUT_TOKENS` | `2048` | one model response limit |
| `QWEN_MAX_TOOL_OUTPUT_CHARS` | `24000` | tool result cap |

## Validation

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
docker build -t qwen-coder-subagent-mcp:test .
```

GitHub Actions runs the same quality gates on pull requests and `main`.
