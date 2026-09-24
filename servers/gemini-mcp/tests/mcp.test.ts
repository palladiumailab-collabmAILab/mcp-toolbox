import { afterEach, describe, expect, it, vi } from "vitest";

import worker from "../src/index";

const env = {
  GEMINI_API_KEY: "test-key",
  MCP_BEARER_TOKEN: "test-bearer-token",
};

async function mcpRequest(method: string, params?: unknown): Promise<Record<string, any>> {
  const response = await worker.fetch(
    new Request("https://gemini-mcp.example.workers.dev/mcp", {
      method: "POST",
      headers: {
        accept: "application/json, text/event-stream",
        authorization: "Bearer test-bearer-token",
        "content-type": "application/json",
        host: "gemini-mcp.example.workers.dev",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    }),
    env,
    {} as ExecutionContext,
  );

  const text = await response.text();
  expect(response.status, text).toBe(200);
  if (response.headers.get("content-type")?.includes("text/event-stream")) {
    const data = text
      .split("\n")
      .find((line) => line.startsWith("data: "))
      ?.slice("data: ".length);
    if (!data) throw new Error(`MCP response did not contain an SSE data event: ${text}`);
    return JSON.parse(data) as Record<string, any>;
  }
  return JSON.parse(text) as Record<string, any>;
}

describe("MCP protocol", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists and calls ask_gemini through JSON-RPC", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ candidates: [{ content: { parts: [{ text: "MCP response" }] } }] }),
      ),
    );

    const initialized = await mcpRequest("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "gemini-mcp-test", version: "1.0.0" },
    });
    expect(initialized.result.serverInfo.name).toBe("Gemini MCP Gateway");

    const listed = await mcpRequest("tools/list", {});
    expect(listed.result.tools.map((tool: { name: string }) => tool.name)).toEqual(["ask_gemini"]);

    const called = await mcpRequest("tools/call", {
      name: "ask_gemini",
      arguments: { prompt: "Reply through MCP" },
    });
    expect(called.result.isError).not.toBe(true);
    expect(called.result.content).toEqual([{ type: "text", text: "MCP response" }]);
  });
});
