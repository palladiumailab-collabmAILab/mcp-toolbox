from pathlib import Path
from types import SimpleNamespace

import pytest

from qwen_image_mcp.engine import QwenImageEngine, _env_bool


class FakeImage:
    def save(self, path: Path) -> None:
        Path(path).write_bytes(b"fake-png")


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(images=[FakeImage()])


class FakeQuantizationConfig:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


def build_engine(tmp_path: Path, pipeline: FakePipeline) -> QwenImageEngine:
    return QwenImageEngine(
        output_dir=tmp_path,
        pipeline=pipeline,
        generator_factory=lambda seed: f"generator:{seed}",
        image_loader=lambda path: f"image:{path}",
    )


def test_generate_uses_official_size_and_transparency_prompt(tmp_path: Path) -> None:
    pipeline = FakePipeline()
    engine = build_engine(tmp_path, pipeline)

    result = engine.generate(
        "a transparent robot sticker",
        aspect_ratio="16:9",
        transparent=True,
        seed=7,
        output_name="../robot",
    )

    call = pipeline.calls[0]
    assert call["width"] == 2752
    assert call["height"] == 1536
    assert call["num_inference_steps"] == 40
    assert call["generator"] == "generator:7"
    assert call["prompt"].startswith("This is an RGBA image with transparency.")
    assert result["quantization"]["backend"] == "bitsandbytes_4bit"
    assert Path(result["path"]).name == "robot.png"
    assert Path(result["path"]).read_bytes() == b"fake-png"


def test_edit_passes_multiple_reference_images(tmp_path: Path) -> None:
    pipeline = FakePipeline()
    engine = build_engine(tmp_path, pipeline)

    result = engine.edit(
        "put both subjects in one scene",
        ["a.png", "b.png"],
        aspect_ratio="4:3",
        num_inference_steps=32,
    )

    call = pipeline.calls[0]
    assert call["image"] == ["image:a.png", "image:b.png"]
    assert call["width"] == 2400
    assert call["height"] == 1792
    assert call["num_inference_steps"] == 32
    assert result["reference_image_count"] == 2


def test_edit_preserves_source_aspect_ratio_by_default(tmp_path: Path) -> None:
    pipeline = FakePipeline()
    engine = build_engine(tmp_path, pipeline)

    result = engine.edit("edit it", ["source.png"])

    call = pipeline.calls[0]
    assert "width" not in call
    assert "height" not in call
    assert result["aspect_ratio"] == "source"
    assert result["width"] is None
    assert result["height"] is None


@pytest.mark.parametrize("count", [0, 11])
def test_edit_rejects_invalid_reference_count(tmp_path: Path, count: int) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    with pytest.raises(ValueError, match="between 1 and 10"):
        engine.edit("edit", [f"{index}.png" for index in range(count)])


def test_invalid_aspect_ratio_is_rejected(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    with pytest.raises(ValueError, match="unsupported aspect_ratio"):
        engine.generate("test", aspect_ratio="5:4")


def test_status_reports_nf4_quantization(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    status = engine.status()
    assert status["model_id"] == "Qwen/Qwen-Image-2.1"
    assert status["model_loaded"] is True
    assert status["quantization_backend"] == "bitsandbytes_4bit"
    assert status["quantization_type"] == "nf4"
    assert status["quantized_components"] == ["transformer", "text_encoder"]


def test_build_quantization_config_quantizes_both_large_components(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    config = engine._build_quantization_config(FakeQuantizationConfig, "bf16")

    assert config.kwargs["quant_backend"] == "bitsandbytes_4bit"
    assert config.kwargs["components_to_quantize"] == ["transformer", "text_encoder"]
    assert config.kwargs["quant_kwargs"] == {
        "load_in_4bit": True,
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_compute_dtype": "bf16",
        "bnb_4bit_use_double_quant": False,
    }


def test_from_env_reads_quantization_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN_IMAGE_QUANT_TYPE", "fp4")
    monkeypatch.setenv("QWEN_IMAGE_DOUBLE_QUANT", "true")

    engine = QwenImageEngine.from_env()

    assert engine.quant_type == "fp4"
    assert engine.double_quant is True


def test_env_bool_rejects_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN_IMAGE_DOUBLE_QUANT", "sometimes")
    with pytest.raises(ValueError, match="must be a boolean"):
        _env_bool("QWEN_IMAGE_DOUBLE_QUANT", default=False)
