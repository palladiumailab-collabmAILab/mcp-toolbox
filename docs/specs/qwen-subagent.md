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

## Component boundaries

- `qwen_mcp.server` exposes the MCP surface.
- `qwen_mcp.agent` owns the bounded agent loop and tool protocol.
- `qwen_mcp.llama_client` is the only component that calls llama.cpp.
- `qwen_mcp.repo_tools` is the only component that can inspect the delegated workspace.

Inference and repository access stay separate: the model requests named operations, while the bridge validates paths, limits, and fixed command arguments before execution.

## Required MCP tools

### `qwen_health`

Checks whether the configured llama.cpp endpoint responds and reports the configured model identifier.

### `qwen_delegate`

Inputs:

- `task`: bounded coding/repository research task.
- `workspace`: absolute or relative repository root accessible to the MCP process.
- `max_rounds`: optional upper bound on local-agent tool iterations.

Behavior:

- Qwen may inspect only the requested workspace and bridge-approved paths.
- Qwen may list files, search text, read text files, inspect `git status`, and inspect unstaged/staged diffs.
- Text search uses `rg` when available and falls back to the bounded Python scanner otherwise.
- Qwen may not edit files, invoke arbitrary commands, commit, push, install dependencies, access VCS internals, read common secret files, or access unrelated paths.
- Model-provided list/search limits are subject to bridge-side hard caps.
- The result is advisory and must contain evidence-oriented findings rather than claiming that changes were applied.

## Security boundary

Every path is resolved against the workspace root. Requests escaping the workspace, including through existing symlinks, are rejected. VCS internals, virtual environments, build/runtime artifacts, local model storage, `.local/`, and common secret files such as `.env` are excluded from the worker surface.

Repository inspection subprocesses are fixed and non-shell. Git status runs with optional locking/index refresh disabled and fsmonitor disabled. Git diff explicitly disables external diff and textconv filters. Submodules are ignored by these inspection commands. Tool inputs and outputs are bounded before being returned to the model.

## Model protocol

The bridge does not depend on model-native function-calling. It requests schema-constrained JSON from llama.cpp with either:

- `kind = "tool"` plus a supported tool and arguments; or
- `kind = "final"` plus the answer.

The system prompt includes complete examples of both envelopes and explicitly tells the model not to emit a native-style `name/arguments` function-call envelope.

For compatibility with observed Qwen output, the bridge normalizes only two bounded deviations before validation:

- an allowed tool emitted as `{"name": ..., "arguments": {...}}` or as `tool/arguments` without `kind`;
- a non-empty `answer` object without `kind`.

Unknown tool names and other malformed responses remain errors. Normalization does not expand the tool allowlist or bypass repository-side argument and path validation.

The HTTP connection pool is reused for all inference rounds in one delegated task and closed when that task ends.

## Target-PC performance policy

The launch path targets Q4_K_M, 16K context, automatic GPU layer placement, Flash Attention, and Q8 KV cache. MoE expert placement is not hard-coded: `tune-model.ps1` benchmarks a bounded set of `n_cpu_moe` candidates with `llama-bench`, stores the fastest successful result under `.local/`, and `start-model.ps1` reuses it. If tuning is unavailable or fails, startup falls back to `--cpu-moe`.

Hardware performance regression checks are intentionally separate from deterministic CI. `benchmark-model.ps1` records prompt-processing and generation throughput on the local machine, supports a local baseline, and fails when either metric drops more than the configured threshold. A baseline is comparable only when model, MoE placement, token counts, CPU, and GPU metadata match the current run; llama.cpp build changes are allowed so backend upgrades can be measured against the same workload.
