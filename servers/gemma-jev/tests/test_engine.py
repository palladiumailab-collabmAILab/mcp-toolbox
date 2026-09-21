import pytest

from gemma_jev.engine import DecisionEngine
from gemma_jev.media_policy import MediaPolicy
from gemma_jev.models import DecisionOption, DecisionRequest


class FakeClient:
    def __init__(self) -> None:
        self.messages = None

    def complete(self, messages):
        self.messages = messages
        return '{"selected_option_id":"A","weights":{"A":4,"B":1},"rationale":"faster"}'


def request(*, image_urls: tuple[str, ...] = ()) -> DecisionRequest:
    return DecisionRequest(
        context="ctx",
        options=(DecisionOption("A", "alpha"), DecisionOption("B", "beta")),
        image_urls=image_urls,
    )


def test_engine_returns_jev_style_result() -> None:
    client = FakeClient()
    engine = DecisionEngine(client)
    result = engine.decide(request())
    assert result.selected_option_id == "A"
    assert result.confidence == 0.8
    assert result.rationale == "faster"
    assert result.latency_ms >= 0
    assert client.messages is not None


def test_engine_rejects_remote_media_before_client_call() -> None:
    client = FakeClient()
    engine = DecisionEngine(client)

    with pytest.raises(ValueError, match="not allowed"):
        engine.decide(request(image_urls=("https://images.example.com/a.png",)))

    assert client.messages is None


def test_engine_accepts_media_allowed_by_shared_policy() -> None:
    client = FakeClient()
    engine = DecisionEngine(
        client,
        media_policy=MediaPolicy(allowed_domains=("images.example.com",)),
    )

    engine.decide(request(image_urls=("https://images.example.com/a.png",)))

    assert client.messages is not None
