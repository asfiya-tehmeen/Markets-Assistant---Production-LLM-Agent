"""Deterministic scoring for the eval harness.

Given a golden-set case's ``expect`` block and the agent's structured response, return the list
of failed checks (empty list == pass). Every check is deterministic — no LLM judge — so a run is
reproducible and cheap enough to gate CI on. Supported expectation keys:

    verdict           exact match against response["verdict"]
    tools_any         at least one of these tools appears in meta.tools_called
    tools_all         every one of these tools appears in meta.tools_called
    tools_none        none of these tools were called
    confidence_min    response confidence is >= this level (low < medium < high)
    confidence_max    response confidence is <= this level
    answer_includes   every substring is present in the answer (case-insensitive)
    answer_excludes   none of these substrings appear in the answer (case-insensitive)
    sources_nonempty  response["sources"] is a non-empty list
"""
from __future__ import annotations

_CONF_ORDER = {"low": 0, "medium": 1, "high": 2}


def _tools_called(response: dict) -> list[str]:
    return list((response.get("meta") or {}).get("tools_called") or [])


def score_case(expect: dict, response: dict) -> list[str]:
    """Return a list of human-readable failure reasons; empty means the case passed."""
    failures: list[str] = []

    if "verdict" in expect:
        actual = response.get("verdict")
        if actual != expect["verdict"]:
            failures.append(f"verdict={actual!r} expected {expect['verdict']!r}")

    called = _tools_called(response)
    if "tools_any" in expect and not any(t in called for t in expect["tools_any"]):
        failures.append(f"tools_called={called} missing any of {expect['tools_any']}")
    if "tools_all" in expect:
        missing = [t for t in expect["tools_all"] if t not in called]
        if missing:
            failures.append(f"tools_called={called} missing all of {missing}")
    if "tools_none" in expect:
        unexpected = [t for t in expect["tools_none"] if t in called]
        if unexpected:
            failures.append(f"tools_called={called} should not include {unexpected}")

    conf = str(response.get("confidence", "low")).lower()
    conf_rank = _CONF_ORDER.get(conf, 0)
    if "confidence_min" in expect:
        floor = _CONF_ORDER.get(expect["confidence_min"], 0)
        if conf_rank < floor:
            failures.append(f"confidence={conf!r} below min {expect['confidence_min']!r}")
    if "confidence_max" in expect:
        ceil = _CONF_ORDER.get(expect["confidence_max"], 2)
        if conf_rank > ceil:
            failures.append(f"confidence={conf!r} above max {expect['confidence_max']!r}")

    answer = str(response.get("answer", "")).lower()
    for sub in expect.get("answer_includes", []):
        if sub.lower() not in answer:
            failures.append(f"answer missing substring {sub!r}")
    for sub in expect.get("answer_excludes", []):
        if sub.lower() in answer:
            failures.append(f"answer contains forbidden substring {sub!r}")

    if expect.get("sources_nonempty") and not response.get("sources"):
        failures.append("sources empty, expected at least one")

    return failures
