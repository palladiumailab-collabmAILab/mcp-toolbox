# Qwen-Image-2.1 MCP development harness

## Invariants

- Keep the server local stdio unless the task explicitly introduces a remote transport.
- Do not commit model weights, generated images, caches, credentials, or machine-specific paths.
- Keep model dependencies optional so deterministic CI does not download or initialize the model.
- Preserve lazy model loading; importing the package must not allocate GPU memory.
- The default runtime must quantize both `transformer` and `text_encoder` with bitsandbytes 4-bit.
- NF4 is the default quantization type; changing precision or disabling quantization requires an explicit task.
- Do not call `.to()` on the pipeline after quantized loading; use Diffusers device dispatch.
- Keep text-to-image and image editing over one shared engine.
- Support at most 10 reference images, matching the upstream model contract.
- Validate observable behavior with Ruff, pytest, and compileall before merge.

## Validation

```text
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m compileall -q src
```

Live model inference is an operator validation step and is not faked by CI.
