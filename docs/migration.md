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

- Qwen: RTX 4060 8GB上で代表的な `qwen_delegate` 実機E2Eと、`n_cpu_moe` の候補別3回以上の性能比較。旧Issue [#4](https://github.com/palladiumailab-collabmAILab/qwen-coder-subagent-mcp/issues/4) の残件。
- Gemini: 実Cloudflare Workerで、`MCP_BEARER_TOKEN` 未設定・不正・正しいトークンのfail-closed動作とMCP呼び出しを確認。旧Issue [#4](https://github.com/palladiumailab-collabmAILab/Gemini_MCP/issues/4) の残件。
- Jev: 実Cloudflare Workerで `/health`、認証拒否、`jev_evaluate` の実推論、機密情報非出力を確認。旧Issue [#2](https://github.com/palladiumailab-collabmAILab/Jev-cloudflare/issues/2) の残件。
- Gemma-Jev: 対応GPU・CUDA・vLLM環境で約51.7GBのDiffusionGemmaを読み込み、`/v1/models` と最小決定要求を確認。旧Issue [#18](https://github.com/palladiumailab-collabmAILab/Gemma-Jev/issues/18) の残件。

## 旧PRの扱い

旧リポジトリに残るCodexハーネス同期PRは、モノレポのルート `AGENTS.md` とルートCIへ整理したため、個別リポジトリの変更としては引き継ぎません。必要なプロジェクト固有ルールは各サービス配下に残しています。
