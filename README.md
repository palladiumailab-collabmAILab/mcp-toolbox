# Gemini MCP

A minimal Cloudflare Workers remote MCP server that exposes one tool, `ask_gemini`, and forwards text prompts to the Gemini API.

## Architecture

```text
MCP client
   |
   | Streamable HTTP /mcp
   v
Cloudflare Worker
   |
   | HTTPS + GEMINI_API_KEY
   v
Gemini API
```

The default model is `gemini-3.5-flash-lite`; callers may select `gemini-3.8-flash`.

## Local development

```bash
npm install
cp .env.example .dev.vars
# edit .dev.vars; never commit it
# For local-only no-token testing, set ALLOW_UNAUTHENTICATED=1.
npm run dev
```

MCP endpoint: `http://localhost:8787/mcp` (use the port printed by Wrangler if different).
Health endpoint: `http://localhost:8787/health`.

## Validation

```bash
npm run validate
docker build -t gemini-mcp .
```

## Cloudflare deployment

Set Worker secrets locally:

```bash
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put MCP_BEARER_TOKEN
npm run deploy
```

`npm run deploy` first verifies that both Worker secrets exist and refuses to deploy if either is missing. The GitHub Actions deployment workflow performs the same preflight with the configured Cloudflare credentials.

Or add repository secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, then run the `Deploy Worker` GitHub Actions workflow. `GEMINI_API_KEY` and `MCP_BEARER_TOKEN` remain Worker secrets and must be provisioned separately.

After deployment:

```text
https://gemini-mcp.<your-subdomain>.workers.dev/mcp
https://gemini-mcp.<your-subdomain>.workers.dev/health
```

## ChatGPT compatibility

This is a standard remote MCP server. ChatGPT can use custom MCP apps only on plans/features where developer mode permits adding the remote endpoint. As of 2026-09-17, arbitrary custom MCP attachment is not available on ChatGPT Plus; current OpenAI documentation limits full MCP to Business/Enterprise/Edu, with limited read/fetch support on Pro.

## Security

The `/mcp` endpoint fails closed when `MCP_BEARER_TOKEN` is missing: remote requests receive `503`, and requests with a missing or wrong token receive `401`. The only unauthenticated mode is an explicit `ALLOW_UNAUTHENTICATED=1` setting on a loopback request (`localhost`, `127.0.0.1`, or `::1`). If a target MCP host requires OAuth, add an OAuth layer before exposing the service to that host.
