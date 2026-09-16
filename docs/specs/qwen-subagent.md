# Qwen coding subagent specification

## Purpose

Expose a local `Qwen3-Coder-30B-A3B-Instruct` model to Codex as a Model Context Protocol (MCP) server. The local model is a bounded, read-only coding worker; Codex remains the orchestrator and authority for repository changes.

## Runtime topology

```text
Codex
  -> stdio MCP (`qwen-mcp`)
  -> persistent local HTTP client
  -> llama.cpp OpenAI-compatible API
  -> Qwen3-Coder-30B-A3B-Instruct Q4_K_M
```

Default llama.cpp endpoint: `http://127.0.0.1:8080/v1`.

## Required MCP tools

### `qwen_health`

Checks whether the configured llama.cpp endpoint responds and reports the configured model identifier.

### `qwen_delegate`

Inputs:

- `task`: bounded coding/repository research task.
- `workspace`: absolute or relative repository root accessible to the MCP process.
- `max_rounds`: optional upper bound on local-agent tool iterations.

Behavior:

- Qwen may inspect only the requested workspace.
- Qwen may list files, search text, read text files, inspect `git status`, and inspect unstaged/staged diffs.
- Text search uses `rg` when available and falls back to the bounded Python scanner otherwise.
- Qwen may not edit files, invoke arbitrary commands, commit, push, install dependencies, or access unrelated paths.
- The result is advisory and must contain evidence-oriented findings rather than claiming that changes were applied.

## Security boundary

Every path is resolved against the workspace root. Requests escaping the workspace, including through existing symlinks, are rejected. Fixed repository inspection subprocesses are the only subprocesses. Tool output is size-bounded before being returned to the model.

## Model protocol

The bridge does not depend on model-native function-calling. It requests schema-constrained JSON from llama.cpp with either:

- `kind = "tool"` plus a supported tool and arguments; or
- `kind = "final"` plus the answer.

The HTTP connection pool is reused for all inference rounds in one delegated task and closed when that task ends.

## Target-PC performance policy

The launch path targets Q4_K_M, 16K context, automatic GPU layer placement, Flash Attention, and Q8 KV cache. MoE expert placement is not hard-coded: `tune-model.ps1` benchmarks a bounded set of `n_cpu_moe` candidates with `llama-bench`, stores the fastest successful result under `.local/`, and `start-model.ps1` reuses it. If tuning is unavailable or fails, startup falls back to `--cpu-moe`.

Hardware performance regression checks are intentionally separate from deterministic CI. `benchmark-model.ps1` records prompt-processing and generation throughput on the local machine, supports a local baseline, and fails when either metric drops more than the configured threshold.
