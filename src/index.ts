import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import {
  DEFAULT_GEMINI_MODEL,
  SUPPORTED_GEMINI_MODELS,
  generateWithGemini,
  type SupportedGeminiModel,
} from "./gemini";

interface Env {
  GEMINI_API_KEY: string;
  GEMINI_MODEL?: SupportedGeminiModel;
  MCP_BEARER_TOKEN?: string;
}

const promptSchema = z
  .string()
  .min(1)
  .max(100_000)
  .describe(
    "Prompt to send to Gemini. Do not include secrets unless the user explicitly requests it.",
  );

function isAuthorized(request: Request, env: Env): boolean {
  if (!env.MCP_BEARER_TOKEN) {
    return true;
  }
  return request.headers.get("authorization") === `Bearer ${env.MCP_BEARER_TOKEN}`;
}

function createServer(env: Env): McpServer {
  const server = new McpServer({
    name: "Gemini MCP Gateway",
    version: "0.1.0",
  });

  server.registerTool(
    "ask_gemini",
    {
      description:
        "Delegate a text task to the Gemini API and return Gemini's text response. Useful for drafting, summarization, transformation, and independent model comparison.",
      inputSchema: z.object({
        prompt: promptSchema,
        model: z.enum(SUPPORTED_GEMINI_MODELS).optional(),
      }),
    },
    async ({ prompt, model }) => {
      try {
        const text = await generateWithGemini({
          apiKey: env.GEMINI_API_KEY,
          prompt,
          model: model ?? env.GEMINI_MODEL ?? DEFAULT_GEMINI_MODEL,
        });
        return {
          content: [{ type: "text", text }],
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown Gemini gateway error";
        return {
          isError: true,
          content: [{ type: "text", text: message }],
        };
      }
    },
  );

  return server;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({
        ok: true,
        service: "gemini-mcp",
        defaultModel: env.GEMINI_MODEL ?? DEFAULT_GEMINI_MODEL,
        authentication: env.MCP_BEARER_TOKEN ? "bearer" : "none",
      });
    }

    if (url.pathname !== "/mcp") {
      return new Response("Not Found", { status: 404 });
    }

    if (!env.GEMINI_API_KEY) {
      return Response.json({ error: "GEMINI_API_KEY is not configured" }, { status: 503 });
    }

    if (!isAuthorized(request, env)) {
      return new Response("Unauthorized", {
        status: 401,
        headers: { "www-authenticate": 'Bearer realm="gemini-mcp"' },
      });
    }

    const handler = createMcpHandler(() => createServer(env));
    return handler(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;
