from gemma_jev.engine import DecisionEngine
from gemma_jev.models import DecisionOption, DecisionRequest


class FakeClient:
    def __init__(self) -> None:
        self.messages = None

    def complete(self, messages):
        self.messages = messages
        return '{"selected_option_id":"A","weights":{"A":4,"B":1},"rationale":"faster"}'


def test_engine_returns_jev_style_result() -> None:
    client = FakeClient()
    engine = DecisionEngine(client)
    result = engine.decide(
        DecisionRequest(
            context="ctx",
            options=(DecisionOption("A", "alpha"), DecisionOption("B", "beta")),
        )
    )
    assert result.selected_option_id == "A"
    assert result.confidence == 0.8
    assert result.rationale == "faster"
    assert result.latency_ms >= 0
    assert client.messages is not None
