# MCPサービス統合記録

2026-09-21時点で、次の既定ブランチを `mcp-toolbox` へ履歴付きで取り込みました。

| 旧リポジトリ | 取り込み先 | 取り込み元コミット |
| --- | --- | --- |
| `qwen-coder-subagent-mcp` | `servers/qwen-coder-subagent-mcp/` | `25015826131ac1849568d78c08f759dfdfd459dd` |
| `Gemini_MCP` | `servers/gemini-mcp/` | `d14076b74b469f4dcfe2ce59ed58f3391dca164c` |
| `Jev-cloudflare` | `servers/jev-cloudflare/` | `883316536ca321c4e8dcb12c6d5860a80db54213` |
| `Gemma-Jev` | `servers/gemma-jev/` | `c72323fa31dedd1a941035857712fcc7cf08c885` |

## 引き継ぐ検証

これらはソース統合や決定的なCIでは代替できないため、必要な環境が整った時点で `mcp-toolbox` 側から実施します。

- Qwen: RTX 4060 8GB上で代表的な `qwen_delegate` 実機E2Eと、`n_cpu_moe` の候補別3回以上の性能比較。[toolbox #1](https://github.com/palladiumailab-collabmAILab/mcp-toolbox/issues/1) で追跡。
- Gemini: Cloudflareへのデプロイ対象から外し、ローカル検証専用へ変更。[toolbox #2](https://github.com/palladiumailab-collabmAILab/mcp-toolbox/issues/2) は方針変更により終了。
- Jev: 実Cloudflare Workerで `/health`、認証拒否、`jev_evaluate` の実推論、機密情報非出力を確認。[toolbox #3](https://github.com/palladiumailab-collabmAILab/mcp-toolbox/issues/3) で追跡。
- Gemma-Jev: 対応GPU・CUDA・vLLM環境で約51.7GBのDiffusionGemmaを読み込み、`/v1/models` と最小決定要求を確認。[toolbox #4](https://github.com/palladiumailab-collabmAILab/mcp-toolbox/issues/4) で追跡。

旧リポジトリ側の対応Issueは移行先をコメントして閉じました。未解決の実環境検証は
Jev、Gemma-Jev、およびQwen-ImageのIssueで追跡します。

## 旧PRの扱い

旧リポジトリに残っていたCodexハーネス同期PRは、モノレポのルート `AGENTS.md` とルートCIへ整理したため、移行先をコメントして閉じました。必要なプロジェクト固有ルールは各サービス配下に残しています。
