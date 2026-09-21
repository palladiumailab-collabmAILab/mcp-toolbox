# vLLM runtime contract

Gemma-Jev's core package and its CPU-only CI do not install vLLM. The serving path has a separate pinned extra so a fresh environment cannot appear complete while `gemma-jev-vllm` is missing its executable.

## Supported matrix

| Component | Supported value |
| --- | --- |
| vLLM | `0.29.0` exactly |
| Python | `3.11` through `3.13` |
| OS/architecture | Linux x86_64 |
| NVIDIA CUDA wheel | CUDA `13.0` prebuilt wheel |
| NVIDIA GPU | Compute capability `7.5` or newer |
| Model | `google/diffusiongemma-26B-A4B-it` at the revision in `src/gemma_jev/model_manifest.json` |

The authoritative machine-readable version is [`src/gemma_jev/vllm_compatibility.json`](../src/gemma_jev/vllm_compatibility.json). The vLLM release is pinned in the `serve` optional dependency in `pyproject.toml`; update both together when changing the serving runtime.

## Fresh install

On a supported Linux NVIDIA host:

```bash
python -m pip install -e ".[serve,model]"
python scripts/download_model.py --dry-run
python scripts/download_model.py
gemma-jev-vllm --check-runtime
gemma-jev-vllm
```

`--check-runtime` executes `vllm --version`, validates the Python range, and fails with an actionable install message if the executable is absent or not exactly `0.29.0`. `--print-only` remains available for CPU-only command inspection and intentionally does not require vLLM to be installed.

The model checkpoint is approximately 51.7 GB. Real startup, `/v1/models`, minimal completion, and structured decision checks require a compatible GPU host and are tracked as separate runtime evidence in Issue #18; they are not faked by the CPU merge gate.
