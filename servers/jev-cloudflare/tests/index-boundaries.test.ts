import { describe, expect, it } from "vitest";

import worker, { type Env } from "../src/index";

const env = {
  AI: {
    run: async () => ({}),
  },
  MCP_BEARER_TOKEN: "server-token",
} as unknown as Env;

describe("worker route boundaries", () => {
  it("returns health only for GET", async () => {
    const getResponse = await worker.fetch(
      new Request("https://worker.example/health", { method: "GET" }),
      env,
    );
    expect(getResponse.status).toBe(200);

    const postResponse = await worker.fetch(
      new Request("https://worker.example/health", { method: "POST" }),
      env,
    );
    expect(postResponse.status).toBe(404);
  });

  it("returns 404 for unknown routes", async () => {
    const response = await worker.fetch(
      new Request("https://worker.example/unknown"),
      env,
    );
    expect(response.status).toBe(404);
  });

  it("rejects unauthenticated MCP requests", async () => {
    const response = await worker.fetch(
      new Request("https://worker.example/mcp", { method: "POST" }),
      env,
    );
    expect(response.status).toBe(401);
  });
});
