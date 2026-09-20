# Project baseline

This project adopts the reusable baseline from `codex-dev-harness`.

## Canonical specifications

Current durable product and system requirements live under `docs/specs/`.

- specifications define what must be true;
- architecture documents explain how the system is structured;
- Issues and PRs describe the current unit of work;
- historical discussion does not override current specifications.

If implementation and a current specification disagree, surface and resolve the conflict.

## Docker baseline

The repository must provide a Docker-based path that can install and start the primary executable environment.

For this repository, the container verifies the Gemma-Jev package and MCP entry point. A real DiffusionGemma/vLLM GPU deployment is an external runtime dependency and is not required for unit CI.

## GitHub CI baseline

GitHub Actions is the canonical remote quality gate for PRs and default-branch pushes.

CI installs development dependencies and invokes the same validation entry point used locally:

```text
python scripts/validate.py --docker
```

The validation script runs:

- `pip check`;
- Ruff lint;
- Ruff format check;
- pytest;
- package build;
- Docker build when `--docker` is supplied.

Do not duplicate this command list in CI. Do not weaken or skip relevant checks merely to make a change mergeable.

## Python baseline: Ruff

Ruff is the standard lint and formatting gate and is executed by the canonical validation script.

## Model asset baseline

Large model binaries are external runtime assets, not source files.

- Track the exact upstream model and revision in `models/manifest.json`.
- Materialize weights into `models/cache/`.
- Keep weight binaries ignored by Git and Docker.
- CI must test acquisition logic without downloading the full model.

## Architecture remains project-specific

The baseline does not prescribe a framework or service topology. Gemma-Jev keeps decision logic in the domain package, with CLI and MCP as adapters over the same `DecisionEngine`.
