import { describe, expect, it } from "vitest";

import {
  allowsLocalUnauthenticated,
  getAuthenticationFailure,
  isAuthorized,
  tokensMatch,
} from "../src/index";
import worker from "../src/index";
import { generateWithGemini } from "../src/gemini";

const protectedEnv = {
  GEMINI_API_KEY: "test-key",
  MCP_BEARER_TOKEN: "a-long-test-token",
};

describe("MCP authentication", () => {
  it("fails closed when the bearer token is missing on a remote request", async () => {
    const request = new Request("https://gemini-mcp.example.workers.dev/mcp");
    const failure = getAuthenticationFailure(request, { GEMINI_API_KEY: "test-key" });

    expect(failure).not.toBeNull();
    if (!failure) {
      throw new Error("Expected missing authentication to fail closed");
    }
    expect(failure.status).toBe(503);
    await expect(failure.json()).resolves.toEqual({
      error: "MCP authentication is not configured",
    });
  });

  it("rejects a missing or incorrect bearer token", () => {
    const missing = new Request("https://gemini-mcp.example.workers.dev/mcp");
    const incorrect = new Request("https://gemini-mcp.example.workers.dev/mcp", {
      headers: { authorization: "Bearer wrong-token" },
    });

    expect(getAuthenticationFailure(missing, protectedEnv)?.status).toBe(401);
    expect(getAuthenticationFailure(incorrect, protectedEnv)?.status).toBe(401);
  });

  it("accepts the configured bearer token without exposing it", () => {
    const request = new Request("https://gemini-mcp.example.workers.dev/mcp", {
      headers: { authorization: "Bearer a-long-test-token" },
    });

    expect(isAuthorized(request, protectedEnv)).toBe(true);
    expect(getAuthenticationFailure(request, protectedEnv)).toBeNull();
    expect(tokensMatch("a-long-test-token", "a-long-test-token")).toBe(true);
    expect(tokensMatch("a-long-test-token", "another-token")).toBe(false);
  });

  it("allows unauthenticated access only with explicit loopback opt-in", () => {
    const local = new Request("http://127.0.0.1:8787/mcp");
    const remote = new Request("https://gemini-mcp.example.workers.dev/mcp");
    const env = { GEMINI_API_KEY: "test-key", ALLOW_UNAUTHENTICATED: "1" };

    expect(allowsLocalUnauthenticated(local, env)).toBe(true);
    expect(isAuthorized(local, env)).toBe(true);
    expect(allowsLocalUnauthenticated(remote, env)).toBe(false);
    expect(isAuthorized(remote, env)).toBe(false);
  });

  it("keeps health public without returning secret values", async () => {
    const response = await worker.fetch(
      new Request("https://gemini-mcp.example.workers.dev/health"),
      { GEMINI_API_KEY: "private-gemini-key", MCP_BEARER_TOKEN: "private-bearer-token" },
      {} as ExecutionContext,
    );
    const body = (await response.json()) as Record<string, unknown>;

    expect(response.status).toBe(200);
    expect(body).toMatchObject({ ok: true, authentication: "bearer" });
    expect(JSON.stringify(body)).not.toContain("private-gemini-key");
    expect(JSON.stringify(body)).not.toContain("private-bearer-token");
  });
});

describe("generateWithGemini", () => {
  it("returns concatenated text parts", async () => {
    const fetcher: typeof fetch = async (input, init) => {
      expect(String(input)).toMatch(/gemini-3\.5-flash-lite:generateContent$/);
      expect(init?.method).toBe("POST");
      expect(new Headers(init?.headers).get("x-goog-api-key")).toBe("test-key");

      return Response.json({
        candidates: [{ content: { parts: [{ text: "hello" }, { text: " world" }] } }],
      });
    };

    await expect(
      generateWithGemini({ apiKey: "test-key", prompt: " test prompt ", fetcher }),
    ).resolves.toBe("hello world");
  });

  it("reports Gemini API errors", async () => {
    const fetcher: typeof fetch = async () =>
      Response.json({ error: { message: "quota exceeded" } }, { status: 429 });

    await expect(
      generateWithGemini({ apiKey: "test-key", prompt: "test", fetcher }),
    ).rejects.toThrow("Gemini API error (429): quota exceeded");
  });

  it("rejects blank prompts", async () => {
    await expect(generateWithGemini({ apiKey: "test-key", prompt: "   " })).rejects.toThrow(
      "Prompt must not be empty",
    );
  });
});
