"""Unit tests for the eval harness scoring logic (eval/scoring.py)."""
from scoring import score_case


def _resp(verdict="ANSWERED", confidence="high", tools=None, answer="", sources=None):
    return {
        "verdict": verdict,
        "confidence": confidence,
        "answer": answer,
        "sources": sources if sources is not None else [],
        "meta": {"tools_called": tools or []},
    }


def test_passing_case_has_no_failures():
    expect = {"verdict": "ANSWERED", "tools_any": ["get_price"], "sources_nonempty": True}
    resp = _resp(tools=["get_price"], sources=["CoinGecko live price"])
    assert score_case(expect, resp) == []


def test_verdict_mismatch_fails():
    fails = score_case({"verdict": "ANSWERED"}, _resp(verdict="NEEDS_HUMAN"))
    assert any("verdict" in f for f in fails)


def test_tools_any_missing_fails():
    fails = score_case({"tools_any": ["calculate"]}, _resp(tools=["get_price"]))
    assert len(fails) == 1


def test_tools_all_partial_fails():
    fails = score_case({"tools_all": ["get_price", "calculate"]}, _resp(tools=["get_price"]))
    assert any("calculate" in f for f in fails)


def test_confidence_min_floor():
    assert score_case({"confidence_min": "medium"}, _resp(confidence="low"))
    assert score_case({"confidence_min": "medium"}, _resp(confidence="high")) == []


def test_confidence_max_ceiling():
    assert score_case({"confidence_max": "low"}, _resp(confidence="high"))
    assert score_case({"confidence_max": "low"}, _resp(confidence="low")) == []


def test_answer_includes_is_case_insensitive():
    assert score_case({"answer_includes": ["Margin"]}, _resp(answer="covers the margin call")) == []
    assert score_case({"answer_includes": ["liquidity"]}, _resp(answer="no match here"))


def test_answer_excludes():
    assert score_case({"answer_excludes": ["guess"]}, _resp(answer="I will guess"))


def test_sources_nonempty():
    assert score_case({"sources_nonempty": True}, _resp(sources=[]))
    assert score_case({"sources_nonempty": True}, _resp(sources=["x"])) == []


def test_missing_meta_treated_as_no_tools():
    # A degraded response without meta should fail a tool expectation, not raise.
    fails = score_case({"tools_any": ["get_price"]}, {"verdict": "NEEDS_HUMAN"})
    assert len(fails) == 1
