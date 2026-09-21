# Jev Cloudflare MCP

Remote MCP server that exposes TypeSafe Jev through Cloudflare Workers AI.

```text
MCP client
  -> HTTPS /mcp
Cloudflare Worker
  -> Workers AI binding
typesafe/jev
```

The Worker exposes one MCP tool, `jev_evaluate`, which evaluates a state against a batch of typed `noul`, `choice`, and `score` questions.

## Security boundary

`/mcp` is fail-closed.

- `MCP_BEARER_TOKEN` missing: HTTP 503
- missing/wrong bearer token: HTTP 401
- valid bearer token: request is passed to the MCP handler
- the Jev model id is fixed to `typesafe/jev`
- state/questions are not written to application logs by this code
- `/health` is public and contains no secret/configuration state

Do not replace the bearer secret with a source-controlled Wrangler variable.

## Requirements

- Cloudflare account with Workers AI access
- Node.js 22+
- Wrangler authentication for deployment

No TypeSafe API key is required for this implementation because Jev is invoked through the Cloudflare Workers AI binding.

## Install

```bash
npm install
npm run check
```

## Local development

Create an untracked `.dev.vars`:

```dotenv
MCP_BEARER_TOKEN=<long-random-token>
```

Then run:

```bash
npm run dev
```

The MCP endpoint is:

```text
http://localhost:8787/mcp
```

## Deploy

Authenticate Wrangler, create the runtime MCP secret, then deploy:

```bash
npx wrangler login
npx wrangler secret put MCP_BEARER_TOKEN
npm run deploy
```

The repository also contains a manual GitHub Actions deployment workflow. Configure repository Actions secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` before using it. The runtime `MCP_BEARER_TOKEN` remains a Cloudflare Worker secret and must already be configured.

## MCP client configuration

Use the deployed Worker URL and pass the bearer token on every MCP request.

```json
{
  "mcpServers": {
    "jev-cloudflare": {
      "url": "https://<worker>.<account>.workers.dev/mcp",
      "headers": {
        "Authorization": "Bearer <MCP_BEARER_TOKEN>"
      }
    }
  }
}
```

Exact configuration syntax differs by MCP client.

## Tool: `jev_evaluate`

Example arguments:

```json
{
  "state": {
    "ticket": {
      "message": "My card was charged twice. Please refund the duplicate."
    }
  },
  "questions": {
    "refund_requested": {
      "type": "noul",
      "instructions": "Does the customer request a refund?",
      "criteria": {
        "true": "A refund is explicitly or clearly requested",
        "false": "No refund is requested"
      }
    },
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {
        "billing": "Payments, charges, invoices, refunds",
        "technical": "Bugs, outages, integrations"
      }
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated is the customer?",
      "criteria": [
        "Calm",
        "Frustrated",
        "Very frustrated"
      ]
    }
  }
}
```

The tool returns the Workers AI Jev response as both MCP text JSON and structured content.

## Limits enforced by this Worker

- maximum 32 questions per call
- maximum request payload represented by the tool arguments: 128 KiB
- instructions: maximum 4,000 characters each
- choice/score: 2 to 32 criteria
- question/choice keys: `A-Z a-z 0-9 _ . -`, maximum 64 characters

Provider-side limits still apply. Jev currently has a 32,000-token context window on Cloudflare Workers AI.

## Endpoints

| Path | Auth | Purpose |
| --- | --- | --- |
| `GET /health` | none | minimal liveness response |
| `/mcp` | Bearer token | MCP Streamable HTTP |
| other | n/a | 404 |

## References

- Cloudflare Jev model: https://developers.cloudflare.com/ai/models/typesafe/jev/
- Workers AI bindings: https://developers.cloudflare.com/workers-ai/configuration/bindings/
- MCP TypeScript SDK web-standard serving: https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/serving/web-standard.md
