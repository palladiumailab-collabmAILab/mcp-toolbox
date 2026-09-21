import { z } from "zod/v4";

export const MAX_QUESTIONS = 32;
export const MAX_REQUEST_BYTES = 128 * 1024;

const instructionsSchema = z.string().trim().min(1).max(4_000);
const criterionTextSchema = z.string().trim().min(1).max(2_000);
const criterionKeySchema = z.string().regex(/^[A-Za-z0-9_.-]{1,64}$/);

const noulQuestionSchema = z
  .object({
    type: z.literal("noul"),
    instructions: instructionsSchema,
    criteria: z
      .object({
        true: criterionTextSchema,
        false: criterionTextSchema,
      })
      .strict()
      .optional(),
  })
  .strict();

const choiceCriteriaSchema = z
  .record(criterionKeySchema, criterionTextSchema)
  .refine((criteria) => {
    const count = Object.keys(criteria).length;
    return count >= 2 && count <= 32;
  }, "choice criteria must contain between 2 and 32 options");

const choiceQuestionSchema = z
  .object({
    type: z.literal("choice"),
    instructions: instructionsSchema,
    criteria: choiceCriteriaSchema,
  })
  .strict();

const scoreQuestionSchema = z
  .object({
    type: z.literal("score"),
    instructions: instructionsSchema,
    criteria: z.array(criterionTextSchema).min(2).max(32),
  })
  .strict();

export const questionSchema = z.discriminatedUnion("type", [
  noulQuestionSchema,
  choiceQuestionSchema,
  scoreQuestionSchema,
]);

const questionsSchema = z
  .record(criterionKeySchema, questionSchema)
  .refine((questions) => {
    const count = Object.keys(questions).length;
    return count >= 1 && count <= MAX_QUESTIONS;
  }, `questions must contain between 1 and ${MAX_QUESTIONS} entries`);

const stateSchema = z.union([
  z.string().min(1),
  z.record(z.string(), z.unknown()),
]);

export const evaluateInputSchema = z
  .object({
    state: stateSchema,
    questions: questionsSchema,
  })
  .strict()
  .superRefine((value, context) => {
    const bytes = new TextEncoder().encode(JSON.stringify(value)).byteLength;
    if (bytes > MAX_REQUEST_BYTES) {
      context.addIssue({
        code: "custom",
        message: `request must be <= ${MAX_REQUEST_BYTES} bytes`,
      });
    }
  });

export type JevEvaluationInput = z.infer<typeof evaluateInputSchema>;
