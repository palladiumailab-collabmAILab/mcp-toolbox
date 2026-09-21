# Qwen-Image-2.1 MCP

Local stdio MCP server for **4-bit Qwen-Image-2.1**.

The runtime loads the official `Qwen/Qwen-Image-2.1` checkpoint and quantizes both the diffusion `transformer` and Qwen3-VL `text_encoder` to bitsandbytes 4-bit at load time. The default quantization type is NF4. The VAE remains in the configured compute dtype.

This is on-the-fly quantization of the official checkpoint, not a separate community checkpoint.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `qwen_image_generate` | Generate an image from text. Supports the upstream 2K aspect-ratio presets and transparent PNG prompting. |
| `qwen_image_edit` | Edit or compose from 1-10 local reference images; preserves source aspect ratio by default. |
| `qwen_image_status` | Report device, dtype, NF4 configuration, dependency presence, output directory, and model load state. |

Generation/edit results also include the active quantization configuration.

## Install

Deterministic development dependencies only:

```powershell
python -m pip install -e ".[dev]"
```

Install the quantized model runtime:

```powershell
python -m pip install -e ".[model]"
```

The model extra installs PyTorch, Accelerate, bitsandbytes, Pillow, Transformers, and the current Diffusers source. Qwen-Image-2.1 is loaded through `QwenImage21Pipeline` with `PipelineQuantizationConfig`.

## Quantization

Default runtime configuration:

- backend: `bitsandbytes_4bit`
- quantization type: `nf4`
- quantized components: `transformer`, `text_encoder`
- compute dtype: `bfloat16`
- nested/double quantization: disabled by default

Diffusers applies 4-bit quantization while loading the official model and dispatches the pipeline directly to the configured device. The implementation intentionally does not call `.to()` after loading the quantized pipeline.

Optional overrides:

| Variable | Default |
| --- | --- |
| `QWEN_IMAGE_QUANT_TYPE` | `nf4` |
| `QWEN_IMAGE_DOUBLE_QUANT` | `false` |

`QWEN_IMAGE_DOUBLE_QUANT=true` enables nested quantization for an additional reduction in weight storage.

## Run

```powershell
qwen-image-mcp
```

Other environment variables:

| Variable | Default |
| --- | --- |
| `QWEN_IMAGE_MODEL_ID` | `Qwen/Qwen-Image-2.1` |
| `QWEN_IMAGE_DEVICE` | `cuda` |
| `QWEN_IMAGE_DTYPE` | `bfloat16` |
| `QWEN_IMAGE_OUTPUT_DIR` | `outputs/qwen-image-2.1` |

Example MCP client entry:

```json
{
  "mcpServers": {
    "qwen-image": {
      "command": "qwen-image-mcp",
      "env": {
        "QWEN_IMAGE_OUTPUT_DIR": "C:/qwen-image-output",
        "QWEN_IMAGE_QUANT_TYPE": "nf4"
      }
    }
  }
}
```

Generated files are PNGs. Reference images are passed as local filesystem paths because this is a local stdio bridge; large image payloads are not copied through MCP JSON.

## Aspect ratios

Generation defaults to `1:1`. Editing defaults to `source`, which leaves width and height unset so the pipeline derives them from the condition image. Explicit presets match the upstream recommended 2K sizes:

- `1:1`: 2048x2048
- `4:3`: 2400x1792
- `3:4`: 1792x2400
- `3:2`: 2528x1696
- `2:3`: 1696x2528
- `16:9`: 2752x1536
- `9:16`: 1536x2752

## Validation

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m compileall -q src
```

CI verifies the quantization contract without downloading model weights or initializing CUDA. Live 4-bit inference remains an operator validation step.
