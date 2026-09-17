# Requirements

## Purpose

Expose a small remote MCP server on Cloudflare Workers that delegates selected text tasks to Google's Gemini API.

## Functional requirements

1. Serve an MCP Streamable HTTP endpoint at `/mcp`.
2. Expose exactly one initial tool, `ask_gemini`.
3. `ask_gemini` accepts a non-empty text prompt and an optional supported Gemini model.
4. The default model is `gemini-3.5-flash-lite`; `gemini-3.8-flash` is also selectable.
5. Return Gemini's text output to the MCP client without adding model-generated text of our own.
6. Expose `/health` without disclosing secrets.
7. Read the Gemini API key only from the Worker secret `GEMINI_API_KEY`.
8. If `MCP_BEARER_TOKEN` is configured, require `Authorization: Bearer <token>` on `/mcp`.

## Non-functional requirements

- Target Cloudflare Workers and current stateless Streamable HTTP MCP handling.
- Keep the server stateless; no Durable Object or database is required.
- Do not log or return secret values.
- Keep the implementation small enough for the Workers Free plan's lightweight request model; Gemini network wait time is external I/O.
- Provide Docker, GitHub Actions validation, and a manual deployment workflow.

## Current product limitation

The server is MCP-compatible, but direct attachment of arbitrary custom MCP apps in ChatGPT depends on the ChatGPT plan and current developer-mode availability. This repository must not claim that ChatGPT Plus can attach the server when the product does not expose that capability.
