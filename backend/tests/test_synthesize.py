"""Unit tests for synthesis helpers — the deterministic 'ground or escalate' backstops."""
import pytest

from app.agent.synthesize import _build_sources, _looks_like_advice


@pytest.mark.parametrize("q", [
    "Should I buy Bitcoin now?",
    "Will Ethereum reach $10000 this year?",
    "What is the best coin to invest in?",
    "How much should I invest in crypto?",
    "Is now a good time to sell?",
    "Give me a price prediction for SOL.",
])
def test_advice_questions_are_flagged(q):
    assert _looks_like_advice(q) is True


@pytest.mark.parametrize("q", [
    "What is liquidation?",
    "What is the current price of Bitcoin?",
    "Explain impermanent loss.",
    "What position size does a 1% risk imply at entry 200 stop 150?",
])
def test_informational_questions_are_not_flagged(q):
    assert _looks_like_advice(q) is False


def test_build_sources_maps_each_tool_type_and_dedupes():
    tool_outputs = [
        {"tool": "search_knowledge_base", "result": {"ok": True, "results": [
            {"id": "g-liquidation", "title": "Liquidation"},
            {"id": "g-liquidation", "title": "Liquidation"},  # duplicate id
        ]}},
        {"tool": "get_price", "result": {"ok": True}},
        {"tool": "calculate", "result": {"ok": True}},
    ]
    sources = _build_sources(tool_outputs)
    ids = [s["id"] for s in sources]
    assert ids == ["kb:g-liquidation", "coingecko", "calculator"]  # deduped, order preserved


def test_build_sources_skips_failed_tools():
    assert _build_sources([{"tool": "get_price", "result": {"ok": False}}]) == []
