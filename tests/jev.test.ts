import { describe, expect, it, vi } from "vitest";

import { JEV_MODEL, runJev } from "../src/jev";

describe("runJev", () => {
  it("always calls the Cloudflare Jev model id", async () => {
    const run = vi.fn(async () => ({
      model: "jev-1.13.0",
      answers: {},
      usage: { input_tokens: 1, output_tokens: 1 },
    }));

    const input = {
      state: "A customer cannot log in.",
      questions: {
        urgent: {
          type: "noul" as const,
          instructions: "Is this urgent?",
        },
      },
    };

    const result = await runJev({ run }, input);

    expect(run).toHaveBeenCalledOnce();
    expect(run).toHaveBeenCalledWith(JEV_MODEL, input);
    expect(result).toMatchObject({ model: "jev-1.13.0" });
  });
});
