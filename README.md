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

The canonical model coordinates are packaged in:

~~~text
src/gemma_jev/model_manifest.json
~~~

This includes the exact Hugging Face repo id and pinned revision used by runtime defaults and the vLLM launcher.

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

Weight binaries remain ignored by Git and Docker.

## Start DiffusionGemma with vLLM

Print the revision-pinned command:

~~~bash
gemma-jev-vllm --print-only
~~~

Start it directly:

~~~bash
gemma-jev-vllm
~~~

After downloading the checkpoint, serve the local files while retaining the same API model name:

~~~bash
gemma-jev-vllm --local
~~~

Additional vLLM arguments can be appended, except media access controls owned by Gemma-Jev (`--allowed-media-domains` and `--allowed-local-media-path`).

DiffusionGemma generation is non-autoregressive, but it is **not** a literal one-forward-pass classifier. vLLM performs iterative denoising over a fixed canvas. The Gemma-Jev hypothesis is that all candidate options can be evaluated jointly within one shared request/canvas, not that the denoising process itself takes only one step.

## Multimodal media security

Remote images are **denied by default**. This follows vLLM's SSRF guidance for remote media fetching.

To allow exact hosts, configure a comma-separated allowlist before starting both vLLM and the MCP/CLI process:

~~~bash
export GEMMA_JEV_ALLOWED_MEDIA_DOMAINS="images.example.com,cdn.example.com"
gemma-jev-vllm
~~~

Gemma-Jev validates every `image_urls` entry against the same exact-host allowlist, and the launcher passes that allowlist to vLLM using `--allowed-media-domains`.

Data image URLs are also disabled by default. Enable only when required:

~~~bash
export GEMMA_JEV_ALLOW_DATA_URLS=1
~~~

Local `file:` URLs and URL userinfo are rejected. Pass-through arguments cannot override the launcher's media-domain or local-media-path controls. Launcher-started vLLM also sets `VLLM_MEDIA_URL_ALLOW_REDIRECTS=0` unless that environment variable was explicitly set by the operator.

## Runtime configuration

The MCP server uses:

~~~text
VLLM_BASE_URL=http://127.0.0.1:8000
VLLM_MODEL=google/diffusiongemma-26B-A4B-it
VLLM_API_KEY=
VLLM_TIMEOUT_S=60
VLLM_MAX_TOKENS=256
GEMMA_JEV_ALLOWED_MEDIA_DOMAINS=
GEMMA_JEV_ALLOW_DATA_URLS=0
~~~

The default model id is loaded from the package manifest. `VLLM_MODEL` remains an explicit override.

Do not commit credentials.

## MCP usage

Start the local stdio server:

~~~bash
gemma-jev-mcp
~~~

The server exposes two tools:

~~~text
decide(
  context: string,
  options: [{id: string, text: string}, ...],
  criteria?: [string, ...],
  image_urls?: [string, ...]
)

status()
~~~

A status response is operational metadata only and never returns the API key.

## CLI usage

~~~bash
gemma-jev examples/decision.json --base-url http://127.0.0.1:8000
~~~

## Benchmark denoising configurations

~~~bash
PYTHONPATH=src python scripts/benchmark.py examples/decision.json \
  --target steps8,http://127.0.0.1:8008,8 \
  --target steps16,http://127.0.0.1:8016,16 \
  --target steps48,http://127.0.0.1:8048,48 \
  --trials 20
~~~

The report includes mean/median/min/max latency and selection agreement for each separately launched server.

## Verification

After installing development dependencies:

~~~bash
python scripts/validate.py
~~~

To include the Docker build, matching the Python 3.13 CI gate:

~~~bash
python scripts/validate.py --docker
~~~

CI validates Python 3.11 and 3.13, checks the built wheel contains the model manifest, and does not require a GPU, live vLLM server, or 50+ GB model download.

## Harness

Repository-local engineering rules and evaluation gates are defined by:

- `AGENTS.md`
- `docs/project-baseline.md`
- `docs/harness-architecture.md`
- `docs/specs/`
- `skills/`
