export const DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite";
export const SUPPORTED_GEMINI_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"] as const;

export type SupportedGeminiModel = (typeof SUPPORTED_GEMINI_MODELS)[number];

type FetchLike = typeof fetch;

interface GeminiGenerateContentResponse {
  candidates?: Array<{
    content?: {
      parts?: Array<{ text?: string }>;
    };
  }>;
  error?: {
    message?: string;
  };
}

export interface GenerateWithGeminiOptions {
  apiKey: string;
  prompt: string;
  model?: SupportedGeminiModel;
  fetcher?: FetchLike;
}

export async function generateWithGemini({
  apiKey,
  prompt,
  model = DEFAULT_GEMINI_MODEL,
  fetcher = fetch,
}: GenerateWithGeminiOptions): Promise<string> {
  const trimmedPrompt = prompt.trim();
  if (!trimmedPrompt) {
    throw new Error("Prompt must not be empty");
  }
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured");
  }

  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const response = await fetcher(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-goog-api-key": apiKey,
    },
    body: JSON.stringify({
      contents: [
        {
          role: "user",
          parts: [{ text: trimmedPrompt }],
        },
      ],
    }),
  });

  let body: GeminiGenerateContentResponse;
  try {
    body = (await response.json()) as GeminiGenerateContentResponse;
  } catch {
    throw new Error(`Gemini API returned a non-JSON response (${response.status})`);
  }

  if (!response.ok) {
    const detail = body.error?.message?.trim();
    throw new Error(
      detail
        ? `Gemini API error (${response.status}): ${detail}`
        : `Gemini API error (${response.status})`,
    );
  }

  const text =
    body.candidates?.[0]?.content?.parts
      ?.map((part) => part.text ?? "")
      .join("")
      .trim() ?? "";

  if (!text) {
    throw new Error("Gemini API returned no text output");
  }

  return text;
}
