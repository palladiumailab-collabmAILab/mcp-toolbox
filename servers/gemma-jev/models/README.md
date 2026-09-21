# Local model cache

Model weight binaries are materialized under `models/cache/` and are intentionally ignored by Git.

The canonical, package-resident model manifest is:

`src/gemma_jev/model_manifest.json`

Use:

```text
python -m pip install -e ".[model]"
python scripts/download_model.py
```

or print the pinned vLLM launch command with:

```text
gemma-jev-vllm --print-only
```
