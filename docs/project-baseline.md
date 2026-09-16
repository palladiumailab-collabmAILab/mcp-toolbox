# Project baseline

This project inherits the reusable baseline from `codex-dev-harness`: durable specifications live under `docs/specs/`, Python uses Ruff, executable paths have Docker reproduction, and GitHub Actions is the remote quality gate.

## Canonical specifications

`docs/specs/` defines required externally meaningful behavior. Architecture documents explain how the implementation satisfies those requirements. If code and specification disagree, surface the conflict instead of silently redefining either side.

## Docker baseline

The MCP bridge must build and run in Docker. The local llama.cpp model server may run on the host GPU; Docker verification must still cover installation, importability, tests, and the bridge executable.

## GitHub CI baseline

Pull requests and pushes to `main` run Ruff lint/format checks, tests, Python bytecode compilation, skill validation, and Docker build verification. Do not weaken checks merely to obtain a green result.

## Python baseline

Use Ruff for lint and format. Keep tests orthogonal to lint. Runtime targets Python 3.11+.
