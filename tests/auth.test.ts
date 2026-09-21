import { describe, expect, it } from "vitest";

import { authorizeMcpRequest } from "../src/auth";

function requestWithToken(token?: string): Request {
  const headers = new Headers();
  if (token !== undefined) {
    headers.set("authorization", `Bearer ${token}`);
  }
  return new Request("https://worker.example/mcp", { headers });
}

describe("authorizeMcpRequest", () => {
  it("fails closed when the server token is not configured", async () => {
    const result = await authorizeMcpRequest(requestWithToken("client-token"), undefined);

    expect(result.authorized).toBe(false);
    if (!result.authorized) {
      expect(result.response.status).toBe(503);
    }
  });

  it("rejects requests without bearer authentication", async () => {
    const result = await authorizeMcpRequest(requestWithToken(), "server-token");

    expect(result.authorized).toBe(false);
    if (!result.authorized) {
      expect(result.response.status).toBe(401);
      expect(result.response.headers.get("www-authenticate")).toContain("Bearer");
    }
  });

  it("rejects the wrong bearer token", async () => {
    const result = await authorizeMcpRequest(requestWithToken("wrong"), "server-token");

    expect(result.authorized).toBe(false);
    if (!result.authorized) {
      expect(result.response.status).toBe(401);
    }
  });

  it("accepts the configured bearer token", async () => {
    const result = await authorizeMcpRequest(
      requestWithToken("server-token"),
      "server-token",
    );

    expect(result).toEqual({ authorized: true });
  });
});
