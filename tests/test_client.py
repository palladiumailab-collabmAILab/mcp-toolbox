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


class RecordingOpener:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.request = None
        self.timeout = None

    def __call__(self, request, timeout):
        self.request = request
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        assert self.payload is not None
        return FakeResponse(self.payload)


def test_complete_uses_injected_transport_and_preserves_request_contract() -> None:
    opener = RecordingOpener(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"selected_option_id":"B","weights":{"A":1,"B":3},'
                            '"rationale":"lower latency"}'
                        )
                    }
                }
            ]
        }
    )
    client = VLLMClient(
        base_url="http://127.0.0.1:8000",
        model="google/diffusiongemma-26B-A4B-it",
        api_key="secret-token",
        timeout_s=3.0,
        max_tokens=128,
        extra_body={"temperature": 0},
        opener=opener,
    )

    content = client.complete([{"role": "user", "content": "choose"}])

    assert '"selected_option_id":"B"' in content
    assert opener.request.full_url == "http://127.0.0.1:8000/v1/chat/completions"
    assert opener.request.get_method() == "POST"
    assert opener.request.headers.get("Authorization") == "Bearer secret-token"
    assert opener.timeout == 3.0
    payload = json.loads(opener.request.data.decode("utf-8"))
    assert payload == {
        "model": "google/diffusiongemma-26B-A4B-it",
        "messages": [{"role": "user", "content": "choose"}],
        "max_tokens": 128,
        "stream": False,
        "temperature": 0,
    }


def test_status_reports_served_model_without_exposing_api_key() -> None:
    opener = RecordingOpener({"data": [{"id": "google/diffusiongemma-26B-A4B-it"}]})
    client = VLLMClient(
        base_url="http://127.0.0.1:8000",
        model="google/diffusiongemma-26B-A4B-it",
        api_key="secret-token",
        timeout_s=3.0,
        opener=opener,
    )

    status = client.status()

    assert opener.request.full_url == "http://127.0.0.1:8000/v1/models"
    assert opener.request.headers.get("Authorization") == "Bearer secret-token"
    assert opener.timeout == 3.0
    assert status == {
        "reachable": True,
        "configured_model": "google/diffusiongemma-26B-A4B-it",
        "served_models": ["google/diffusiongemma-26B-A4B-it"],
        "model_available": True,
        "error": None,
    }
    assert "secret-token" not in repr(status)


def test_status_distinguishes_http_error_from_connection_failure() -> None:
    request_url = "http://127.0.0.1:8000/v1/models"
    opener = RecordingOpener(error=HTTPError(request_url, 401, "Unauthorized", None, None))
    client = VLLMClient(
        base_url="http://127.0.0.1:8000",
        model="expected",
        opener=opener,
    )

    assert client.status() == {
        "reachable": True,
        "configured_model": "expected",
        "served_models": [],
        "model_available": False,
        "error": "http_401",
    }


def test_status_handles_connection_failure() -> None:
    opener = RecordingOpener(error=URLError("offline"))
    client = VLLMClient(
        base_url="http://127.0.0.1:8000",
        model="expected",
        opener=opener,
    )

    assert client.status() == {
        "reachable": False,
        "configured_model": "expected",
        "served_models": [],
        "model_available": False,
        "error": "connection_error",
    }
