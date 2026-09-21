import math

import pytest

from gemma_jev.models import DecisionOption, DecisionRequest
from gemma_jev.protocol import build_messages, normalize_weights, parse_decision


def request() -> DecisionRequest:
    return DecisionRequest(
        context="ctx",
        criteria=("latency",),
        options=(DecisionOption("A", "alpha"), DecisionOption("B", "beta")),
    )


def test_build_messages_places_every_option_on_one_request() -> None:
    messages = build_messages(request())
    assert len(messages) == 2
    user = messages[1]["content"]
    assert isinstance(user, str)
    assert '"id":"A"' in user
    assert '"id":"B"' in user
    assert "alpha" in user and "beta" in user


def test_build_messages_supports_images() -> None:
    req = DecisionRequest(
        context="ctx",
        options=(DecisionOption("A", "alpha"), DecisionOption("B", "beta")),
        image_urls=("https://example.com/a.png",),
    )
    content = build_messages(req)[1]["content"]
    assert isinstance(content, list)
    assert content[1]["image_url"]["url"] == "https://example.com/a.png"


def test_parse_decision_normalizes_weights() -> None:
    selected, weights, rationale = parse_decision(
        '~~~json\n{"selected_option_id":"B","weights":{"A":1,"B":3},"rationale":"r"}\n~~~',
        ("A", "B"),
    )
    assert selected == "B"
    assert math.isclose(weights["A"], 0.25)
    assert math.isclose(weights["B"], 0.75)
    assert rationale == "r"


def test_parse_decision_repairs_unknown_selection_by_argmax() -> None:
    selected, weights, _ = parse_decision(
        '{"selected_option_id":"X","probabilities":{"A":2,"B":1}}',
        ("A", "B"),
    )
    assert selected == "A"
    assert weights["A"] > weights["B"]


def test_normalize_weights_accepts_list_shape() -> None:
    weights = normalize_weights(
        [{"id": "A", "weight": 2}, {"id": "B", "probability": 2}],
        ("A", "B"),
    )
    assert weights == {"A": 0.5, "B": 0.5}


def test_zero_weights_are_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_weights({"A": 0, "B": 0}, ("A", "B"))


def test_duplicate_option_ids_are_rejected() -> None:
    with pytest.raises(ValueError):
        DecisionRequest(
            context="ctx",
            options=(DecisionOption("A", "one"), DecisionOption("A", "two")),
        )
