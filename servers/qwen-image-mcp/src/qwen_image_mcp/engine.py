from __future__ import annotations

import importlib.util
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

MODEL_ID = "Qwen/Qwen-Image-2.1"
ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "1:1": (2048, 2048),
    "4:3": (2400, 1792),
    "3:4": (1792, 2400),
    "3:2": (2528, 1696),
    "2:3": (1696, 2528),
    "16:9": (2752, 1536),
    "9:16": (1536, 2752),
}

GeneratorFactory = Callable[[int], Any]
ImageLoader = Callable[[str], Any]


class QwenImageEngine:
    def __init__(
        self,
        *,
        model_id: str = MODEL_ID,
        device: str = "cuda",
        dtype: str = "bfloat16",
        output_dir: str | Path = "outputs/qwen-image-2.1",
        pipeline: Any | None = None,
        generator_factory: GeneratorFactory | None = None,
        image_loader: ImageLoader | None = None,
    ) -> None:
        self.model_id = model_id
        self.device = device
        self.dtype = dtype
        self.output_dir = Path(output_dir).expanduser()
        self._pipeline = pipeline
        self._generator_factory = generator_factory
        self._image_loader = image_loader

    @classmethod
    def from_env(cls) -> QwenImageEngine:
        return cls(
            model_id=os.getenv("QWEN_IMAGE_MODEL_ID", MODEL_ID),
            device=os.getenv("QWEN_IMAGE_DEVICE", "cuda"),
            dtype=os.getenv("QWEN_IMAGE_DTYPE", "bfloat16"),
            output_dir=os.getenv("QWEN_IMAGE_OUTPUT_DIR", "outputs/qwen-image-2.1"),
        )

    def status(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "device": self.device,
            "dtype": self.dtype,
            "output_dir": str(self.output_dir.expanduser().resolve()),
            "model_loaded": self._pipeline is not None,
            "torch_installed": importlib.util.find_spec("torch") is not None,
            "diffusers_installed": importlib.util.find_spec("diffusers") is not None,
            "pillow_installed": importlib.util.find_spec("PIL") is not None,
        }

    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
        num_inference_steps: int = 40,
        seed: int = 42,
        transparent: bool = False,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        prompt = self._validate_prompt(prompt)
        width, height = self._size_for(aspect_ratio)
        steps = self._validate_steps(num_inference_steps)
        seed = self._validate_seed(seed)
        effective_prompt = self._transparent_prompt(prompt) if transparent else prompt

        result = self._get_pipeline()(
            prompt=effective_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            generator=self._make_generator(seed),
        )
        image = result.images[0]
        output_path = self._save_image(image, output_name)
        return {
            "path": str(output_path),
            "model_id": self.model_id,
            "prompt": prompt,
            "effective_prompt": effective_prompt,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "num_inference_steps": steps,
            "seed": seed,
            "transparent_requested": transparent,
        }

    def edit(
        self,
        prompt: str,
        image_paths: list[str],
        *,
        aspect_ratio: str = "source",
        num_inference_steps: int = 40,
        seed: int = 42,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        prompt = self._validate_prompt(prompt)
        if not 1 <= len(image_paths) <= 10:
            raise ValueError("image_paths must contain between 1 and 10 images")

        size_kwargs: dict[str, int] = {}
        if aspect_ratio != "source":
            width, height = self._size_for(aspect_ratio)
            size_kwargs = {"width": width, "height": height}
        steps = self._validate_steps(num_inference_steps)
        seed = self._validate_seed(seed)
        images = [self._load_image(path) for path in image_paths]
        image_arg: Any = images[0] if len(images) == 1 else images

        result = self._get_pipeline()(
            prompt=prompt,
            image=image_arg,
            num_inference_steps=steps,
            generator=self._make_generator(seed),
            **size_kwargs,
        )
        image = result.images[0]
        output_path = self._save_image(image, output_name)
        return {
            "path": str(output_path),
            "model_id": self.model_id,
            "prompt": prompt,
            "reference_image_count": len(images),
            "width": size_kwargs.get("width"),
            "height": size_kwargs.get("height"),
            "aspect_ratio": aspect_ratio,
            "num_inference_steps": steps,
            "seed": seed,
        }

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        try:
            import torch
            from diffusers import QwenImage21Pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Qwen-Image runtime dependencies are missing; "
                'install with python -m pip install -e ".[model]"'
            ) from exc

        torch_dtype = getattr(torch, self.dtype, None)
        if torch_dtype is None:
            raise ValueError(f"unsupported torch dtype: {self.dtype}")
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("QWEN_IMAGE_DEVICE requests CUDA, but CUDA is not available")

        pipeline = QwenImage21Pipeline.from_pretrained(
            self.model_id,
            dtype=torch_dtype,
        )
        self._pipeline = pipeline.to(self.device)
        return self._pipeline

    def _make_generator(self, seed: int) -> Any:
        if self._generator_factory is not None:
            return self._generator_factory(seed)

        try:
            import torch
        except ImportError as exc:
            raise RuntimeError(
                'PyTorch is missing; install with python -m pip install -e ".[model]"'
            ) from exc
        return torch.Generator(self.device).manual_seed(seed)

    def _load_image(self, path: str) -> Any:
        if self._image_loader is not None:
            return self._image_loader(path)

        image_path = Path(path).expanduser()
        if not image_path.is_file():
            raise ValueError(f"reference image does not exist: {image_path}")

        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                'Pillow is missing; install with python -m pip install -e ".[model]"'
            ) from exc

        with Image.open(image_path) as image:
            return image.copy()

    def _save_image(self, image: Any, output_name: str | None) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        name = Path(output_name).name if output_name else f"qwen-image-{uuid4().hex[:12]}.png"
        if not name.lower().endswith(".png"):
            name += ".png"
        output_path = (self.output_dir / name).resolve()
        image.save(output_path)
        return output_path

    @staticmethod
    def _validate_prompt(prompt: str) -> str:
        value = prompt.strip()
        if not value:
            raise ValueError("prompt must not be empty")
        return value

    @staticmethod
    def _validate_steps(value: int) -> int:
        if not 1 <= value <= 200:
            raise ValueError("num_inference_steps must be between 1 and 200")
        return value

    @staticmethod
    def _validate_seed(value: int) -> int:
        if not 0 <= value < 2**63:
            raise ValueError("seed must be between 0 and 2^63 - 1")
        return value

    @staticmethod
    def _size_for(aspect_ratio: str) -> tuple[int, int]:
        try:
            return ASPECT_RATIOS[aspect_ratio]
        except KeyError as exc:
            supported = ", ".join(ASPECT_RATIOS)
            raise ValueError(
                f"unsupported aspect_ratio {aspect_ratio!r}; choose one of: {supported}"
            ) from exc

    @staticmethod
    def _transparent_prompt(prompt: str) -> str:
        return (
            "This is an RGBA image with transparency. "
            f"{prompt}. "
            "The image has alpha channel and the background is transparent."
        )
