import { describe, expect, it, vi } from "vitest";

import worker from "../src/index";

async function mcpRequest(method: string, params?: unknown): Promise<Record<string, any>> {
  const run = vi.fn(async () => ({
    model: "jev-1.13.0",
    answers: { urgent: true },
    usage: { input_tokens: 3, output_tokens: 1 },
  }));
  const response = await worker.fetch(
    new Request("https://jev.example.workers.dev/mcp", {
      method: "POST",
      headers: {
        accept: "application/json, text/event-stream",
        authorization: "Bearer test-bearer-token",
        "content-type": "application/json",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    }),
    { AI: { run }, MCP_BEARER_TOKEN: "test-bearer-token" },
  );

  expect(response.status).toBe(200);
  const text = await response.text();
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
  it("lists and calls jev_evaluate through JSON-RPC", async () => {
    const initialized = await mcpRequest("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "jev-mcp-test", version: "1.0.0" },
    });
    expect(initialized.result.serverInfo.name).toBe("jev-cloudflare-mcp");

    const listed = await mcpRequest("tools/list", {});
    expect(listed.result.tools.map((tool: { name: string }) => tool.name)).toEqual([
      "jev_evaluate",
    ]);

    const called = await mcpRequest("tools/call", {
      name: "jev_evaluate",
      arguments: {
        state: { ticket: { message: "The service is unavailable." } },
        questions: {
          urgent: {
            type: "noul",
            instructions: "Is this urgent?",
          },
        },
      },
    });
    expect(called.result.isError).not.toBe(true);
    expect(called.result.structuredContent.result.answers).toEqual({ urgent: true });
  });
});
