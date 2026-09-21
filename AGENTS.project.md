# Project-specific Codex instructions

## Project purpose

Maintain the Qwen coding subagent MCP and its constrained repository-access bridge.

## Source of truth

- `docs/specs/qwen-subagent.md`: model/backend contract and durable Qwen-subagent requirements.

## Qwen subagent boundary

- Treat Qwen as a read-only worker. Do not give it target-repository file writes, arbitrary shell, git commit/push, or external network access.
- Expose only the MCP's bounded repository tools such as list, search, read, `git status`, and `git diff`.
- Normalize paths under the configured workspace, reject symlink-mediated escape, and block secrets, VCS internals, runtime-generated data, and other worker-unnecessary areas at the bridge.
- Treat Qwen output as proposals/research. The parent Codex applies changes, runs validation, and makes the final decision.
- Update `docs/specs/qwen-subagent.md` before changing the model or inference backend.

## Model routing

- Parent: `gpt-5.6-sol / medium` for implementation, architecture, debugging, review, and final integration.
- OpenAI bounded worker: `gpt-5.6-luna / max`.
- Local read-only worker: `Qwen3-Coder-30B-A3B-Instruct Q4_K_M`.
- Do not finalize a change from the local worker's conclusion alone; the parent must inspect the diff and verification evidence.
- `QWEN_ALLOWED_WORKSPACE_ROOTS` に明示された top-level Git worktree だけを delegated workspace として許可する。未設定、home、兄弟repo、非Gitディレクトリは default deny とする。
