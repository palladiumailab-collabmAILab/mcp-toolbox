import { describe, expect, it } from "vitest";

import { generateWithGemini } from "../src/gemini";

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
