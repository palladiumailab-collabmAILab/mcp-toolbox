import type { JevEvaluationInput } from "./schema";

export const JEV_MODEL = "typesafe/jev";

export interface WorkersAiBinding {
  run(model: string, input: unknown): Promise<unknown>;
}

export async function runJev(
  ai: WorkersAiBinding,
  input: JevEvaluationInput,
): Promise<unknown> {
  return ai.run(JEV_MODEL, input);
}
