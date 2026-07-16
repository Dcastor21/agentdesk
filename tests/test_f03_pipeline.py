"""F03 — Pipeline happy path: topic in, all node outputs visible in state."""

import pytest
from pipeline.graph import graph

_TOPIC = "The history of the Python programming language"
_TEXT_KEYS = ("plan", "research", "summary", "critique", "draft", "final")
_ALL_KEYS = _TEXT_KEYS + ("score",)


async def test_all_node_outputs_present(require_anthropic):
    result = await graph.ainvoke({"topic": _TOPIC})

    for key in _ALL_KEYS:
        assert key in result, f"state missing key: '{key}'"


async def test_text_outputs_are_substantive(require_anthropic):
    result = await graph.ainvoke({"topic": _TOPIC})

    for key in _TEXT_KEYS:
        assert isinstance(result[key], str), f"'{key}' should be str, got {type(result[key])}"
        assert len(result[key]) > 50, f"'{key}' suspiciously short ({len(result[key])} chars)"

    # Final is the polished artifact — expect at least 400 chars
    assert len(result["final"]) >= 400, (
        f"'final' too short for a research article ({len(result['final'])} chars)"
    )


async def test_critic_score_is_valid(require_anthropic):
    result = await graph.ainvoke({"topic": _TOPIC})

    assert isinstance(result["score"], float), f"score should be float, got {type(result['score'])}"
    assert 0.0 <= result["score"] <= 1.0, f"score out of range: {result['score']}"
