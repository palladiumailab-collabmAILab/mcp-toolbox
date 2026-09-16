---
name: "github-operations"
description: "Use only when the user explicitly asks to create, inspect, synchronize, push, pull, branch, or otherwise mutate a GitHub repository."
---

# GitHub operations

1. Verify the exact repository, visibility, default branch, and intended write scope.
2. Preserve unrelated changes and prefer a `codex/...` branch for non-trivial changes.
3. Make one reviewable change set where possible; never force-push by default.
4. Run proportionate checks before proposing the change.
5. Verify GitHub Actions for the pushed commit or PR. Missing or failing expected CI is a blocker, not success.
6. Do not write secrets, tokens, `.env`, private keys, dumps, or machine-specific credentials.
