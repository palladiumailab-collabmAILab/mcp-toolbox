# MCP Toolbox

MCPサーバー、ローカルMCPブリッジ、モデル連携ツールを一つのモノレポで管理するための保管庫です。

## 収録サービス

| サービス | 種別 | MCPツール | 実行環境 |
| --- | --- | --- | --- |
| [`qwen-coder-subagent-mcp`](servers/qwen-coder-subagent-mcp/) | ローカルstdioブリッジ | `qwen_health`, `qwen_delegate` | Windows / llama.cpp / Qwen |
| [`gemini-mcp`](servers/gemini-mcp/) | リモートMCP | `ask_gemini` | Cloudflare Workers / Gemini API |
| [`jev-cloudflare`](servers/jev-cloudflare/) | リモートMCP | `jev_evaluate` | Cloudflare Workers AI / TypeSafe Jev |
| [`gemma-jev`](servers/gemma-jev/) | ローカルstdioサーバー | `decide`, `status` | Python / vLLM / DiffusionGemma |
| [`qwen-image-mcp`](servers/qwen-image-mcp/) | ローカルstdioサーバー | `qwen_image_generate`, `qwen_image_edit`, `qwen_image_status` | Python / Diffusers / bitsandbytes NF4 / Qwen-Image-2.1 |

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

# Qwen-Image-2.1（transformer + text_encoderを4-bit NF4量子化、CIでは実モデル未ロード）
Set-Location ../qwen-image-mcp
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m compileall -q src
```

## Cloudflare連携

このモノレポからCloudflareへデプロイできる対象はJevだけです。Geminiは
ローカル検証対象として残し、Cloudflareへのデプロイ経路は持ちません。

Jevをデプロイする場合だけ、専用の `Deploy Jev MCP` ワークフローを手動実行し、
`CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID` をGitHub ActionsのSecretsに
設定します。Worker側の `MCP_BEARER_TOKEN` はCloudflare側で個別に管理します。

通常のCIはCloudflareへの実デプロイを行わず、各サービスのローカル検証と
Wrangler dry-runだけを実行します。

Qwen Coder、Qwen-Image-2.1、Gemma-Jevはローカルstdio MCPです。GPU・モデル・ローカル環境を必要とするライブ推論は、ルートCIでは実行せず、モデルダウンロードも行いません。

## 統合方針

このモノレポへの統合元は次の4リポジトリです。

- `qwen-coder-subagent-mcp`
- `Gemini_MCP`
- `Jev-cloudflare`
- `Gemma-Jev`

各サービスの実装は `servers/` 配下に履歴付きで取り込みました。Cloudflareへ
公開するデプロイ単位はJevだけに限定し、MCP共通化が必要になった場合は、
認証・health・スキーマなどを個別サービスの契約を壊さない範囲で共有パッケージへ
切り出します。
