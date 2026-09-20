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

The MCP implementation uses the current stable MCP Python SDK v2 and stdio by default.

## CLI usage

~~~bash
gemma-jev examples/decision.json --base-url http://127.0.0.1:8000
~~~

## Start DiffusionGemma with vLLM

Use a vLLM build/image with DiffusionGemma support. A representative launch is:

~~~bash
docker run --rm --gpus all --ipc=host --network host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:gemma \
  --model google/diffusiongemma-26B-A4B-it \
  --max-num-seqs 4 \
  --generation-config vllm \
  --gpu-memory-utilization 0.85 \
  --hf-overrides '{"diffusion_sampler":"entropy_bound","diffusion_entropy_bound":0.1}' \
  --diffusion-config '{"canvas_length":256}' \
  --host 0.0.0.0 --port 8000
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

~~~bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m build
docker build -t gemma-jev:local .
~~~

The MCP test uses the SDK's in-process client and a fake completion client, so unit CI does not require a GPU or model server.

## Harness

Repository-local engineering rules and evaluation gates are defined by:

- `AGENTS.md`
- `docs/project-baseline.md`
- `docs/harness-architecture.md`
- `docs/specs/`
- `skills/`

See issue #2 for the harness/MCP integration acceptance criteria.
