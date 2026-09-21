import { describe, expect, it } from "vitest";

import { evaluateInputSchema, MAX_QUESTIONS } from "../src/schema";

describe("evaluateInputSchema", () => {
  it("accepts a batched noul, choice, and score request", () => {
    const parsed = evaluateInputSchema.parse({
      state: { ticket: "My payment failed twice." },
      questions: {
        urgent: {
          type: "noul",
          instructions: "Is this urgent?",
          criteria: {
            true: "Needs immediate handling",
            false: "Can wait",
          },
        },
        department: {
          type: "choice",
          instructions: "Which team should handle this?",
          criteria: {
            billing: "Payment and invoice issues",
            technical: "Product bugs",
          },
        },
        frustration: {
          type: "score",
          instructions: "How frustrated is the customer?",
          criteria: ["Calm", "Frustrated", "Very frustrated"],
        },
      },
    });

    expect(Object.keys(parsed.questions)).toHaveLength(3);
  });

  it("rejects an empty question map", () => {
    expect(() =>
      evaluateInputSchema.parse({ state: "test", questions: {} }),
    ).toThrow();
  });

  it("rejects more than the configured question limit", () => {
    const questions = Object.fromEntries(
      Array.from({ length: MAX_QUESTIONS + 1 }, (_, index) => [
        `q${index}`,
        {
          type: "noul",
          instructions: "Is this true?",
        },
      ]),
    );

    expect(() =>
      evaluateInputSchema.parse({ state: "test", questions }),
    ).toThrow();
  });

  it("requires at least two choice criteria", () => {
    expect(() =>
      evaluateInputSchema.parse({
        state: "test",
        questions: {
          route: {
            type: "choice",
            instructions: "Choose a route.",
            criteria: { only: "Only option" },
          },
        },
      }),
    ).toThrow();
  });
});
