# Gemini MCP project instructions

This repository follows the reusable baseline from `codex-dev-harness`.

- Treat `docs/specs/` as the canonical source for durable product/system requirements.
- Keep changes minimal and scoped to the requested behavior.
- Do not commit API keys, access tokens, `.dev.vars`, `.env`, or other secrets.
- Keep a Docker-based reproducible validation path.
- GitHub Actions is the canonical remote quality gate for PRs and `main` pushes.
- Before completion, run format, lint, type-check, tests, Worker dry-run build, and Docker build when available.
- Do not weaken validation only to make CI pass.
- Production deployment is an explicit action. Cloudflare and Gemini credentials must be provided through secrets, never source files.
