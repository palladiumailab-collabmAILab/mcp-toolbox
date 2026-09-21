# Project-specific Codex instructions

## Project purpose

- Maintain a remote MCP server that exposes TypeSafe Jev through Cloudflare Workers AI with a small, typed, fail-closed interface.

## Project-specific sources of truth

- `README.md`: public behavior, security boundary, deployment and client configuration.
- `src/schema.ts`: input contract and request limits.
- `src/auth.ts`: MCP authentication boundary.
- `wrangler.jsonc`: Worker runtime/binding configuration.
- `package.json`: canonical local verification commands.

## Project-specific invariants

- Keep `/mcp` fail-closed: missing runtime bearer configuration must not make the endpoint public.
- Keep `MCP_BEARER_TOKEN` out of source-controlled Wrangler variables and repository files; it is a runtime secret.
- Keep the Jev model binding explicit and do not silently switch providers/models without updating the documented contract and tests.
- Do not log raw bearer tokens or unnecessarily persist user-supplied state/questions.
- Preserve the typed `noul` / `choice` / `score` contract and repository-owned request limits unless the change is explicit and tested.
- Deployment is an external write and must be explicitly requested.

## Project verification

- Canonical local gate: `npm run check`.
- Security-sensitive auth/schema changes require focused regression tests in addition to typecheck and Wrangler dry-run.
