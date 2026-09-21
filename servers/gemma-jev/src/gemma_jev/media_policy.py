from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

_ALLOWED_SCHEMES = {"http", "https"}
_TRUTHY = {"1", "true", "yes", "on"}


def _normalize_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if not domain:
        raise ValueError("media domain must be non-empty")
    if any(char in domain for char in "/:@"):
        raise ValueError(f"media domain must be a hostname only: {value!r}")
    return domain


def parse_allowed_media_domains(value: str | None) -> tuple[str, ...]:
    if not value or not value.strip():
        return ()
    normalized = (_normalize_domain(part) for part in value.split(",") if part.strip())
    return tuple(dict.fromkeys(normalized))


@dataclass(frozen=True, slots=True)
class MediaPolicy:
    allowed_domains: tuple[str, ...] = ()
    allow_data_urls: bool = False

    @classmethod
    def from_env(cls) -> "MediaPolicy":
        return cls(
            allowed_domains=parse_allowed_media_domains(
                os.getenv("GEMMA_JEV_ALLOWED_MEDIA_DOMAINS")
            ),
            allow_data_urls=os.getenv("GEMMA_JEV_ALLOW_DATA_URLS", "").strip().lower() in _TRUTHY,
        )

    def validate_url(self, url: str) -> None:
        if url.lower().startswith("data:"):
            if not self.allow_data_urls:
                raise ValueError(
                    "data image URLs are disabled; set GEMMA_JEV_ALLOW_DATA_URLS=1 to enable them"
                )
            if not url.lower().startswith("data:image/"):
                raise ValueError("only image data URLs are supported")
            return

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
        except ValueError as exc:
            raise ValueError(f"malformed image URL: {url!r}") from exc

        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise ValueError("image URLs must use http or https, or an explicitly enabled data URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("image URLs with userinfo are not allowed")
        if not hostname:
            raise ValueError(f"image URL is missing a hostname: {url!r}")

        domain = hostname.lower().rstrip(".")
        if domain not in self.allowed_domains:
            raise ValueError(
                f"image URL domain {domain!r} is not allowed; configure "
                "GEMMA_JEV_ALLOWED_MEDIA_DOMAINS with exact hostnames"
            )

    def validate_urls(self, urls: tuple[str, ...]) -> None:
        for url in urls:
            self.validate_url(url)
