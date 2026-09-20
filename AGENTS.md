# Gemma-Jev development harness

This repository adopts the operating model from `codex-dev-harness` with project-local scope.

## Invariants

- Preserve the requested outcome and explicit acceptance criteria.
- Read the relevant `docs/specs/` document before changing observable behavior or external interfaces.
- Treat tests, lint, builds, CI, and benchmarks as evidence, not as substitutes for the requested outcome.
- Do not weaken tests, thresholds, or acceptance criteria merely to obtain a pass.
- Keep CLI and MCP as adapters over the same domain implementation; do not duplicate decision logic.
- Preserve unrelated changes. Do not use destructive reset/clean/force-push as a default recovery action.
- Never commit credentials, tokens, private keys, `.env` files, or machine-specific secrets.
- Do not add unrelated frameworks, services, or broad refactors.

## Conditional guidance

Read only when relevant:

- Executable Python, Docker reproducibility, GitHub Actions, Ruff, or canonical specifications:
  `docs/project-baseline.md`
- Task contracts, evaluation decisions, or repeated improvement:
  `docs/harness-architecture.md`
- Explicit GitHub branch/commit/Issue/PR/CI operations:
  `skills/github-operations/SKILL.md`
- Iterative optimization against an explicit baseline:
  `skills/self-improvement/SKILL.md`

## Project verification

For implementation changes, the canonical merge gate is:

1. `python -m ruff check .`
2. `python -m ruff format --check .`
3. `python -m pytest -q`
4. `python -m build`
5. `docker build .`
6. required GitHub Actions checks pass on the PR

A change is not complete while required evaluation is unresolved.
