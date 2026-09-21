import { createMcpHandler, McpServer } from "@modelcontextprotocol/server";
import { z } from "zod/v4";

import { authorizeMcpRequest } from "./auth";
import { JEV_MODEL, runJev, type WorkersAiBinding } from "./jev";
import { evaluateInputSchema } from "./schema";

export interface Env {
  AI: WorkersAiBinding;
  MCP_BEARER_TOKEN?: string;
}

function buildServer(env: Env): McpServer {
  const server = new McpServer({
    name: "jev-cloudflare-mcp",
    version: "0.1.0",
  });

  server.registerTool(
    "jev_evaluate",
    {
      description:
        "Evaluate one state against one or more typed Jev questions. Supports noul, choice, and score questions and returns Jev's calibrated structured decision result.",
      inputSchema: evaluateInputSchema,
      outputSchema: z.object({
        result: z.unknown(),
      }),
    },
    async (input) => {
      try {
        const result = await runJev(env.AI, input);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result),
            },
          ],
          structuredContent: { result },
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        console.error("Jev inference failed:", message);
        return {
          content: [
            {
              type: "text",
              text: "Jev inference failed.",
            },
          ],
          isError: true,
        };
      }
    },
  );

  return server;
}

function healthResponse(): Response {
  return Response.json(
    {
      status: "ok",
      service: "jev-cloudflare-mcp",
      model: JEV_MODEL,
    },
    {
      headers: {
        "cache-control": "no-store",
      },
    },
  );
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health" && request.method === "GET") {
      return healthResponse();
    }

    if (url.pathname !== "/mcp") {
      return Response.json({ error: "Not found." }, { status: 404 });
    }

    const auth = await authorizeMcpRequest(request, env.MCP_BEARER_TOKEN);
    if (!auth.authorized) {
      return auth.response;
    }

    const handler = createMcpHandler(() => buildServer(env));
    return handler.fetch(request);
  },
};
