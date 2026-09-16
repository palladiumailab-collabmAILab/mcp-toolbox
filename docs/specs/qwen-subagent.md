# Qwen coding subagent specification

## Purpose

Expose a local `Qwen3-Coder-30B-A3B-Instruct` model to Codex as a Model Context Protocol (MCP) server. The local model is a bounded, read-only coding worker; Codex remains the orchestrator and authority for repository changes.

## Runtime topology

```text
Codex
  -> stdio MCP (`qwen-mcp`)
  -> local llama.cpp OpenAI-compatible HTTP API
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
- Qwen may not edit files, invoke arbitrary commands, commit, push, install dependencies, or access unrelated paths.
- The result is advisory and must contain evidence-oriented findings rather than claiming that changes were applied.

## Security boundary

Every path is resolved against the workspace root. Requests escaping the workspace, including through existing symlinks, are rejected. Fixed `git` subcommands are the only subprocesses. Tool output is size-bounded before being returned to the model.

## Model protocol

The bridge does not depend on model-native function-calling. It requests schema-constrained JSON from llama.cpp with either:

- `kind = "tool"` plus a supported tool and arguments; or
- `kind = "final"` plus the answer.

This keeps the agent loop deterministic across llama.cpp chat-template changes.

## Defaults for the target PC

The launch script targets Q4_K_M with a 16K context, CPU-resident MoE experts, automatic GPU layer placement, Flash Attention, and Q8 KV cache. These are starting defaults and may be tuned after local measurement.
