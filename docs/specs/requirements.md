# Gemma-Jev requirements

## Purpose

Gemma-Jev exposes a compact structured decision layer over a DiffusionGemma model served through an OpenAI-compatible vLLM endpoint.

## Core decision contract

A decision request contains:

- free-form context;
- at least two options with unique non-empty ids and non-empty text;
- optional decision criteria;
- optional image URLs.

A decision result contains:

- one selected option id;
- one normalized non-negative decision weight for every supplied option;
- a concise rationale;
- measured model-request latency.

Returned decision weights are not claimed to be calibrated probabilities.

## Shared decision engine

CLI and MCP interfaces must call the same `DecisionEngine` implementation. Interface adapters may perform serialization and configuration but must not duplicate decision semantics.

## CLI

The `gemma-jev` executable remains available for manual execution, debugging, and benchmarking.

## MCP

The `gemma-jev-mcp` executable exposes a local MCP server.

Requirements:

- default transport is stdio;
- the server exposes a `decide` tool;
- the tool accepts context, options, optional criteria, and optional image URLs;
- the tool returns structured decision data;
- importing the module must not start the server;
- application logging must not write arbitrary text to stdout while stdio transport is active.

## Runtime configuration

The MCP server reads vLLM connection configuration from environment variables:

- `VLLM_BASE_URL`
- `VLLM_MODEL`
- `VLLM_API_KEY`
- `VLLM_TIMEOUT_S`
- `VLLM_MAX_TOKENS`

No credential may be embedded in source or committed configuration.

## Verification

Unit and MCP protocol tests must not require a GPU or live model server. End-to-end DiffusionGemma latency, stability, and calibration are empirical evaluations performed against target hardware separately from the unit merge gate.
