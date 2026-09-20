import json
from urllib.error import HTTPError, URLError

from gemma_jev.client import VLLMClient


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_status_reports_served_model_without_exposing_api_key(monkeypatch) -> None:
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.headers.get("Authorization")
        seen["timeout"] = timeout
        return FakeResponse({"data": [{"id": "google/diffusiongemma-26B-A4B-it"}]})

    monkeypatch.setattr("gemma_jev.client.urlopen", fake_urlopen)
    client = VLLMClient(
        base_url="http://127.0.0.1:8000",
        model="google/diffusiongemma-26B-A4B-it",
        api_key="secret-token",
        timeout_s=3.0,
    )

    status = client.status()

    assert seen["url"] == "http://127.0.0.1:8000/v1/models"
    assert seen["authorization"] == "Bearer secret-token"
    assert seen["timeout"] == 3.0
    assert status == {
        "reachable": True,
        "configured_model": "google/diffusiongemma-26B-A4B-it",
        "served_models": ["google/diffusiongemma-26B-A4B-it"],
        "model_available": True,
        "error": None,
    }
    assert "secret-token" not in repr(status)


def test_status_distinguishes_http_error_from_connection_failure(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", None, None)

    monkeypatch.setattr("gemma_jev.client.urlopen", fake_urlopen)
    client = VLLMClient(base_url="http://127.0.0.1:8000", model="expected")

    assert client.status() == {
        "reachable": True,
        "configured_model": "expected",
        "served_models": [],
        "model_available": False,
        "error": "http_401",
    }


def test_status_handles_connection_failure(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr("gemma_jev.client.urlopen", fake_urlopen)
    client = VLLMClient(base_url="http://127.0.0.1:8000", model="expected")

    assert client.status() == {
        "reachable": False,
        "configured_model": "expected",
        "served_models": [],
        "model_available": False,
        "error": "connection_error",
    }
