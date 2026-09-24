# MCP Toolbox

This repository is the monorepo for reusable MCP servers and local MCP bridges.

## Layout

- `servers/qwen-coder-subagent-mcp/`: local, read-only Qwen coding subagent bridge.
- `servers/gemini-mcp/`: Gemini Worker implementation retained for local validation only; production deployment is disabled in this monorepo.
- `servers/jev-cloudflare/`: Cloudflare Workers remote MCP server for TypeSafe Jev.
- `servers/gemma-jev/`: local stdio MCP server and CLI for DiffusionGemma-backed decisions.
- `servers/qwen-image-mcp/`: local stdio MCP server for Qwen-Image-2.1 generation and editing.
- `.github/workflows/`: the only active repository CI and deployment workflows.

Each server keeps its own project-specific requirements and tests. The nearest service-level `AGENTS.md` remains applicable inside that service directory.

## Invariants

- Do not commit credentials, model weights, `.env`, `.dev.vars`, local caches, or machine-specific settings.
- Preserve the security boundaries of each service when reorganizing code.
- Qwen remains read-only and workspace-allowlisted.
- Worker MCP endpoints remain fail-closed when their runtime bearer configuration is missing.
- Gemma-Jev CLI and MCP adapters must continue to share one `DecisionEngine`.
- Do not deploy or change external secrets from local validation.

## Validation

Run the service-specific checks from each service directory. The root GitHub Actions workflow runs the same deterministic gates for all five services.

- Qwen: `python -m ruff check .`, `python -m ruff format --check .`, `python -m pytest -q`, Docker build.
- Gemini: `npm run validate`, Docker build.
- Jev: `npm run check`.
- Gemma-Jev: `python scripts/validate.py --docker` on the supported Python 3.13 CI leg.
- Qwen Image: `python -m ruff check .`, `python -m ruff format --check .`, `python -m pytest -q`, `python -m compileall -q src`.

The GPU model download, live vLLM validation, and live Jev Cloudflare deployment are separate operator actions and are not faked by CI.
