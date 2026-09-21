# MCP Toolbox

MCPサーバー、ローカルMCPブリッジ、モデル連携ツールを一つのモノレポで管理するための保管庫です。

## 収録サービス

| サービス | 種別 | MCPツール | 実行環境 |
| --- | --- | --- | --- |
| [`qwen-coder-subagent-mcp`](servers/qwen-coder-subagent-mcp/) | ローカルstdioブリッジ | `qwen_health`, `qwen_delegate` | Windows / llama.cpp / Qwen |
| [`gemini-mcp`](servers/gemini-mcp/) | リモートMCP | `ask_gemini` | Cloudflare Workers / Gemini API |
| [`jev-cloudflare`](servers/jev-cloudflare/) | リモートMCP | `jev_evaluate` | Cloudflare Workers AI / TypeSafe Jev |
| [`gemma-jev`](servers/gemma-jev/) | ローカルstdioサーバー | `decide`, `status` | Python / vLLM / DiffusionGemma |

各サービスは独立した依存関係・設定・検証手順を維持し、ルートのGitHub Actionsがまとめて品質ゲートを実行します。モデル重み、APIキー、Cloudflareシークレットはリポジトリに含めません。

## ディレクトリ構成

```text
mcp-toolbox/
├── servers/
│   ├── qwen-coder-subagent-mcp/
│   ├── gemini-mcp/
│   ├── jev-cloudflare/
│   └── gemma-jev/
├── .github/workflows/
│   ├── ci.yml       # 4サービスの検証
│   └── deploy.yml   # Gemini/Jevの手動デプロイ
└── README.md
```

移行時点の未完了な実環境検証は [`docs/migration.md`](docs/migration.md) に記録しています。

## ローカル検証

サービスごとの正本手順は各ディレクトリのREADMEとAGENTSを参照してください。

```powershell
# Qwen
Set-Location servers/qwen-coder-subagent-mcp
python -m ruff check .
python -m ruff format --check .
python -m pytest -q

# Gemini
Set-Location ../gemini-mcp
npm install --ignore-scripts
npm run validate

# Jev
Set-Location ../jev-cloudflare
npm install --ignore-scripts
npm run check

# Gemma-Jev（GPU・モデル重み不要の品質ゲート）
Set-Location ../gemma-jev
python scripts/validate.py
```

## デプロイ

Cloudflare Workerのデプロイは、GitHub Actionsの `Deploy MCP service` を手動実行し、`gemini` または `jev` を選択します。Cloudflare認証情報と各WorkerのランタイムシークレットはGitHub/CloudflareのSecretsで管理します。

- Gemini: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`、Worker側の `GEMINI_API_KEY`, `MCP_BEARER_TOKEN`
- Jev: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`、Worker側の `MCP_BEARER_TOKEN`

QwenとGemma-Jevはローカルstdio MCPであり、GPU・モデル・ローカル環境を必要とするため、ルートのCIではライブモデル起動やモデルダウンロードを行いません。

## 統合方針

このモノレポへの統合元は次の4リポジトリです。

- `qwen-coder-subagent-mcp`
- `Gemini_MCP`
- `Jev-cloudflare`
- `Gemma-Jev`

各サービスの実装は `servers/` 配下に履歴付きで取り込みました。Cloudflare Workerのデプロイ単位はサービスごとに維持し、MCP共通化が必要になった場合は、認証・health・スキーマなどを個別サービスの契約を壊さない範囲で共有パッケージへ切り出します。
