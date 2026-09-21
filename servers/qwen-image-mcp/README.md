# Qwen-Image-2.1 MCP

Local stdio MCP server for `Qwen/Qwen-Image-2.1`.

The server exposes text-to-image generation, image editing with up to 10 local reference images, transparent PNG generation, and a lightweight status tool. Model loading is lazy, so starting or testing the package does not download weights or allocate GPU memory.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `qwen_image_generate` | Generate an image from text. Supports official 2K aspect-ratio presets and transparent PNG prompting. |
| `qwen_image_edit` | Edit or compose from 1-10 local reference images; preserves the source aspect ratio by default. |
| `qwen_image_status` | Report configuration, dependency presence, output directory, and whether the model is loaded. |

## Install

Deterministic development dependencies only:

```powershell
python -m pip install -e ".[dev]"
```

Install the model runtime as well:

```powershell
python -m pip install -e ".[model]"
```

The model extra follows the upstream Qwen-Image-2.1 requirements and installs the current Diffusers source because Qwen-Image-2.1 support ships through `QwenImage21Pipeline`.

## Run

```powershell
qwen-image-mcp
```

Default environment:

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
        "QWEN_IMAGE_OUTPUT_DIR": "C:/qwen-image-output"
      }
    }
  }
}
```

Generated files are PNGs. Reference images are passed as local filesystem paths because this server is a local stdio bridge; large image payloads are not copied through MCP JSON.

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

CI never downloads `Qwen/Qwen-Image-2.1`. A live GPU inference check remains a separate operator action.
