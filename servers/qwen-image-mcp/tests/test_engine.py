from pathlib import Path
from types import SimpleNamespace

import pytest

from qwen_image_mcp.engine import QwenImageEngine


class FakeImage:
    def save(self, path: Path) -> None:
        Path(path).write_bytes(b"fake-png")


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(images=[FakeImage()])


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


@pytest.mark.parametrize("count", [0, 11])
def test_edit_rejects_invalid_reference_count(tmp_path: Path, count: int) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    with pytest.raises(ValueError, match="between 1 and 10"):
        engine.edit("edit", [f"{index}.png" for index in range(count)])


def test_invalid_aspect_ratio_is_rejected(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    with pytest.raises(ValueError, match="unsupported aspect_ratio"):
        engine.generate("test", aspect_ratio="5:4")


def test_status_reports_injected_pipeline_as_loaded(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, FakePipeline())
    status = engine.status()
    assert status["model_id"] == "Qwen/Qwen-Image-2.1"
    assert status["model_loaded"] is True
