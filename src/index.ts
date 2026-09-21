import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import {
  DEFAULT_GEMINI_MODEL,
  SUPPORTED_GEMINI_MODELS,
  generateWithGemini,
  type SupportedGeminiModel,
} from "./gemini";

export interface Env {
  GEMINI_API_KEY: string;
  GEMINI_MODEL?: SupportedGeminiModel;
  MCP_BEARER_TOKEN?: string;
  ALLOW_UNAUTHENTICATED?: string;
}

const promptSchema = z
  .string()
  .min(1)
  .max(100_000)
  .describe(
    "Prompt to send to Gemini. Do not include secrets unless the user explicitly requests it.",
  );

const LOOPBACK_HOSTNAMES = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

function isLoopbackRequest(request: Request): boolean {
  return LOOPBACK_HOSTNAMES.has(new URL(request.url).hostname);
}

export function tokensMatch(provided: string, expected: string): boolean {
  const providedBytes = new TextEncoder().encode(provided);
  const expectedBytes = new TextEncoder().encode(expected);
  const length = Math.max(providedBytes.length, expectedBytes.length);
  let difference = providedBytes.length ^ expectedBytes.length;

  for (let index = 0; index < length; index += 1) {
    difference |= (providedBytes[index] ?? 0) ^ (expectedBytes[index] ?? 0);
  }

  return difference === 0;
}

export function allowsLocalUnauthenticated(request: Request, env: Env): boolean {
  return env.ALLOW_UNAUTHENTICATED === "1" && isLoopbackRequest(request);
}

export function isAuthorized(request: Request, env: Env): boolean {
  if (!env.MCP_BEARER_TOKEN) {
    return allowsLocalUnauthenticated(request, env);
  }

  return tokensMatch(request.headers.get("authorization") ?? "", `Bearer ${env.MCP_BEARER_TOKEN}`);
}

export function getAuthenticationFailure(request: Request, env: Env): Response | null {
  if (!env.MCP_BEARER_TOKEN && !allowsLocalUnauthenticated(request, env)) {
    return Response.json(
      { error: "MCP authentication is not configured" },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }

  if (!isAuthorized(request, env)) {
    return new Response("Unauthorized", {
      status: 401,
      headers: {
        "cache-control": "no-store",
        "www-authenticate": 'Bearer realm="gemini-mcp"',
      },
    });
  }

  return null;
}

function authenticationMode(request: Request, env: Env): "bearer" | "local-opt-in" | "required" {
  if (env.MCP_BEARER_TOKEN) {
    return "bearer";
  }
  if (allowsLocalUnauthenticated(request, env)) {
    return "local-opt-in";
  }
  return "required";
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
        authentication: authenticationMode(request, env),
      });
    }

    if (url.pathname !== "/mcp") {
      return new Response("Not Found", { status: 404 });
    }

    const authenticationFailure = getAuthenticationFailure(request, env);
    if (authenticationFailure) {
      return authenticationFailure;
    }

    if (!env.GEMINI_API_KEY) {
      return Response.json(
        { error: "GEMINI_API_KEY is not configured" },
        { status: 503, headers: { "cache-control": "no-store" } },
      );
    }

    const handler = createMcpHandler(() => createServer(env));
    return handler(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;
