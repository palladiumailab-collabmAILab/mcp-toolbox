# MCP Toolbox

MCPサーバー、ローカルMCPブリッジ、モデル連携ツールを一つのモノレポで管理するための保管庫です。

## 収録サービス

| サービス | 種別 | MCPツール | 実行環境 |
| --- | --- | --- | --- |
| [`qwen-coder-subagent-mcp`](servers/qwen-coder-subagent-mcp/) | ローカルstdioブリッジ | `qwen_health`, `qwen_delegate` | Windows / llama.cpp / Qwen |
| [`gemini-mcp`](servers/gemini-mcp/) | リモートMCP | `ask_gemini` | Cloudflare Workers / Gemini API |
| [`jev-cloudflare`](servers/jev-cloudflare/) | リモートMCP | `jev_evaluate` | Cloudflare Workers AI / TypeSafe Jev |
| [`gemma-jev`](servers/gemma-jev/) | ローカルstdioサーバー | `decide`, `status` | Python / vLLM / DiffusionGemma |
| [`qwen-image-mcp`](servers/qwen-image-mcp/) | ローカルstdioサーバー | `qwen_image_generate`, `qwen_image_edit`, `qwen_image_status` | Python / Diffusers / Qwen-Image-2.1 |

各サービスは独立した依存関係・設定・検証手順を維持し、ルートのGitHub Actionsがまとめて品質ゲートを実行します。モデル重み、APIキー、Cloudflareシークレットはリポジトリに含めません。

## ディレクトリ構成

```text
mcp-toolbox/
├── servers/
│   ├── qwen-coder-subagent-mcp/
│   ├── gemini-mcp/
│   ├── jev-cloudflare/
│   ├── gemma-jev/
│   └── qwen-image-mcp/
├── .github/workflows/
│   ├── ci.yml              # 5サービスの検証
│   ├── deploy-gemini.yml   # Gemini Workerの手動デプロイ
│   └── deploy-jev.yml      # Jev Workerの手動デプロイ
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

# Qwen-Image-2.1（実モデルは任意依存、CIでは未ロード）
Set-Location ../qwen-image-mcp
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m compileall -q src
```

## デプロイ

Cloudflare Workerはサービスごとに独立してデプロイします。GitHub Actionsから対象サービス専用のワークフローを手動実行してください。

- Gemini: `Deploy Gemini MCP`
- Jev: `Deploy Jev MCP`

両ワークフローは別々のWorkerへデプロイされ、一方の実行や失敗が他方のデプロイを開始・停止させることはありません。Cloudflare認証情報と各WorkerのランタイムシークレットはGitHub/CloudflareのSecretsで管理します。

- Gemini: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`、Worker側の `GEMINI_API_KEY`, `MCP_BEARER_TOKEN`
- Jev: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`、Worker側の `MCP_BEARER_TOKEN`

初回のActionsデプロイ前に、各WorkerのランタイムシークレットをWranglerまたはCloudflare Dashboardで個別に登録してください。Geminiは必須シークレットが未登録の場合、デプロイ前検査で停止します。Jevはシークレットが未登録でもWorker自体は配置できますが、`/mcp` は設定完了まで `503` を返します。

Qwen Coder、Qwen-Image-2.1、Gemma-Jevはローカルstdio MCPです。GPU・モデル・ローカル環境を必要とするライブ推論は、ルートCIでは実行せず、モデルダウンロードも行いません。

## 統合方針

このモノレポへの統合元は次の4リポジトリです。

- `qwen-coder-subagent-mcp`
- `Gemini_MCP`
- `Jev-cloudflare`
- `Gemma-Jev`

各サービスの実装は `servers/` 配下に履歴付きで取り込みました。Cloudflare Workerのデプロイ単位はサービスごとに維持し、MCP共通化が必要になった場合は、認証・health・スキーマなどを個別サービスの契約を壊さない範囲で共有パッケージへ切り出します。
