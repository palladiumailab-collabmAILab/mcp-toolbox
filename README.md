# Gemma-Jev

Prototype of a **Jev-style structured decision layer** on top of DiffusionGemma served by vLLM.

The core idea is to place every candidate option in one request/canvas, let DiffusionGemma jointly condition the denoising process on that shared context, and return a compact structured decision distribution.

## Interfaces

Gemma-Jev exposes the same `DecisionEngine` through two adapters:

- **MCP** — primary agent integration;
- **CLI** — manual debugging, scripts, and benchmarks.

The returned weights are **not assumed to be calibrated probabilities**.

## Install

~~~bash
python -m pip install -e .
~~~

For development:

~~~bash
python -m pip install -e ".[dev]"
~~~

## Model weights

The model binary is intentionally **not committed to Git**. The upstream checkpoint is roughly 51.7 GB and split into 11 safetensors shards.

The exact model coordinates are tracked in `models/manifest.json`, including a pinned upstream revision.

Install the optional downloader and materialize that revision locally:

~~~bash
python -m pip install -e ".[model]"
python scripts/download_model.py --dry-run
python scripts/download_model.py
~~~

The default destination is:

~~~text
models/cache/diffusiongemma-26B-A4B-it
~~~

That directory and common weight formats are ignored by Git and Docker. To intentionally update the model version, change and review `models/manifest.json`; do not manually copy weight binaries into the repository.

## Runtime configuration

The MCP server uses:

~~~text
VLLM_BASE_URL=http://127.0.0.1:8000
VLLM_MODEL=google/diffusiongemma-26B-A4B-it
VLLM_API_KEY=
VLLM_TIMEOUT_S=60
VLLM_MAX_TOKENS=256
~~~

Do not commit credentials.

## MCP usage

Start the local stdio server:

~~~bash
gemma-jev-mcp
~~~

Configure an MCP host to launch that command and provide the vLLM environment variables. The server exposes one tool:

~~~text
decide(
  context: string,
  options: [{id: string, text: string}, ...],
  criteria?: [string, ...],
  image_urls?: [string, ...]
)
~~~

It returns structured data:

~~~json
{
  "selected_option_id": "B",
  "weights": {"A": 0.2, "B": 0.8},
  "confidence": 0.8,
  "rationale": "lower expected latency",
  "latency_ms": 183.2
}
~~~

## CLI usage

~~~bash
gemma-jev examples/decision.json --base-url http://127.0.0.1:8000
~~~

## Start DiffusionGemma with vLLM

The tracked model manifest is the source of truth for the intended model revision. When serving directly from Hugging Face, use the same model id/revision.

A representative vLLM launch is:

~~~bash
vllm serve "google/diffusiongemma-26B-A4B-it"
~~~

DiffusionGemma is non-autoregressive at generation time, but it is not a literal one-forward-pass classifier. vLLM performs iterative denoising over a fixed canvas.

## Benchmark denoising configurations

~~~bash
PYTHONPATH=src python scripts/benchmark.py examples/decision.json \
  --target steps8,http://127.0.0.1:8008,8 \
  --target steps16,http://127.0.0.1:8016,16 \
  --target steps48,http://127.0.0.1:8048,48 \
  --trials 20
~~~

The report includes mean/median/min/max latency and selection agreement for each server.

## Verification

After installing development dependencies, run the single canonical local gate:

~~~bash
python scripts/validate.py
~~~

To include the Docker build, matching CI:

~~~bash
python scripts/validate.py --docker
~~~

The MCP and model-asset tests use fake/in-process clients. CI does not require a GPU, live vLLM server, or 50+ GB model download.

## Harness

Repository-local engineering rules and evaluation gates are defined by:

- `AGENTS.md`
- `docs/project-baseline.md`
- `docs/harness-architecture.md`
- `docs/specs/`
- `skills/`
