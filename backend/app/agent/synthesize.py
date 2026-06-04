"""Synthesis node: turn collected tool outputs into the structured, grounded response.

This is where "grounding over guessing" is enforced. The LLM produces a draft, then
deterministic backstops force ``NEEDS_HUMAN`` for: no grounded data, regulated/personalized
advice, or weak retrieval with no hard data — regardless of what the model claimed.
"""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, field_validator

# Patterns that indicate a request for personalized/regulated advice or predictions.
_ADVICE_PATTERNS = [
    r"\bshould i (buy|sell|invest|hold|short|long|put|trade)",
    r"\bis \w[\w\s]* a (good|bad|smart|safe) (buy|investment|idea|bet)",
    r"\b(price )?prediction\b",
    r"\bwill .*(go up|go down|moon|crash|reach|hit \$?\d|double|pump|dump)",
    r"\bwhat should i (buy|sell|invest|do with|put my money)",
    r"\bhow much should i invest",
    r"\bis (now|it) a good time to (buy|sell|invest)",
    r"\b(which|what) (coin|crypto|token|asset) should i",
    # "what is the best coin to invest in", "which token to buy", "top crypto to hold"
    r"\b(best|top|which|what) (coin|crypto|cryptocurrency|token|asset|stock)s? "
    r"(to (buy|invest|trade|hold|pick|get)|should i)",
]

_SYSTEM = (
    "You are Markets Assistant, a careful finance/markets information agent. "
    "You answer ONLY using the TOOL RESULTS provided to you. Never use outside knowledge to "
    "state facts, prices, or figures. Respond with a SINGLE JSON object with exactly these keys:\n"
    '  "answer": string — concise, grounded in the tool results.\n'
    '  "used_source_ids": array of strings — each MUST be one of the provided source ids; [] if none.\n'
    '  "confidence": one of "high", "medium", "low".\n'
    '  "verdict": "ANSWERED" or "NEEDS_HUMAN".\n'
    "Set verdict=NEEDS_HUMAN and do NOT fabricate when ANY of these hold: the tool results are "
    "empty or insufficient to answer; the question is out of scope (not about finance/markets); "
    "or it asks for personalized or regulated investment advice (buy/sell/hold recommendations, "
    "price predictions, or tax/legal advice). When NEEDS_HUMAN, briefly explain why in 'answer' "
    "and suggest consulting a qualified human; do not guess."
)


class _Draft(BaseModel):
    """Validated shape of the LLM's JSON output."""

    answer: str
    used_source_ids: list[str] = []
    confidence: Literal["high", "medium", "low"] = "low"
    verdict: Literal["ANSWERED", "NEEDS_HUMAN"] = "NEEDS_HUMAN"

    @field_validator("confidence", mode="before")
    @classmethod
    def _norm_conf(cls, v):
        v = str(v).lower().strip()
        return v if v in ("high", "medium", "low") else "low"

    @field_validator("verdict", mode="before")
    @classmethod
    def _norm_verdict(cls, v):
        v = str(v).upper().strip()
        return v if v in ("ANSWERED", "NEEDS_HUMAN") else "NEEDS_HUMAN"


def _build_sources(tool_outputs: list[dict]) -> list[dict]:
    """Map raw tool outputs to citable source entries the model may reference by id."""
    sources: list[dict] = []
    for out in tool_outputs:
        result = out.get("result", {})
        if out["tool"] == "search_knowledge_base" and result.get("ok"):
            for hit in result.get("results", []):
                sources.append({"id": f"kb:{hit['id']}", "label": hit["title"]})
        elif out["tool"] == "get_price" and result.get("ok"):
            sources.append({"id": "coingecko", "label": "CoinGecko live price"})
        elif out["tool"] == "calculate" and result.get("ok"):
            sources.append({"id": "calculator", "label": "Deterministic calculator"})
    # De-duplicate while preserving order.
    seen, unique = set(), []
    for s in sources:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    return unique


def _looks_like_advice(question: str) -> bool:
    q = question.lower()
    return any(re.search(p, q) for p in _ADVICE_PATTERNS)


def synthesize_response(llm, state: dict) -> tuple[dict, dict]:
    """Produce the final structured response dict and the token usage for this call."""
    tool_outputs = state["tool_outputs"]
    sources = _build_sources(tool_outputs)
    context = {
        "question": state["question"],
        "tool_results": tool_outputs,
        "available_sources": sources,
    }
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": "Answer using ONLY the data below. Respond with a single JSON "
                                    "object.\n\n" + json.dumps(context, default=str)},
    ]

    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    try:
        resp = llm.chat(messages=messages, response_format={"type": "json_object"}, temperature=0.0)
        usage = {"prompt_tokens": resp.usage.prompt_tokens,
                 "completion_tokens": resp.usage.completion_tokens}
        draft = _Draft(**json.loads(resp.choices[0].message.content))
    except Exception:
        return ({"answer": "I hit an internal error while composing the answer, so I'm escalating "
                           "rather than guessing.",
                 "sources": [], "confidence": "low", "verdict": "NEEDS_HUMAN"}, usage)

    id_to_label = {s["id"]: s["label"] for s in sources}
    used = [id_to_label[i] for i in draft.used_source_ids if i in id_to_label]

    # --- Deterministic grounding-over-guessing backstops ---
    forced_reason: str | None = None
    if _looks_like_advice(state["question"]):
        forced_reason = ("this asks for personalized or regulated investment advice (e.g. whether "
                         "to buy/sell or a price prediction), which I'm not able to give.")
    elif not tool_outputs:
        forced_reason = "I don't have enough grounded information from my tools to answer reliably."
    elif state.get("retrieval_weak") and not any(
        o["tool"] in ("get_price", "calculate") for o in tool_outputs
    ):
        forced_reason = "my knowledge base didn't contain a close enough match to answer reliably."

    if forced_reason:
        answer = (f"I'm escalating this to a human rather than guessing, because {forced_reason} "
                  "Please consult a qualified professional or rephrase within scope.")
        return ({"answer": answer, "sources": [], "confidence": "low",
                 "verdict": "NEEDS_HUMAN"}, usage)

    confidence = draft.confidence
    if draft.verdict == "ANSWERED" and state.get("retrieval_weak") and confidence == "high":
        confidence = "medium"  # don't claim high confidence on weak retrieval

    return ({"answer": draft.answer, "sources": used, "confidence": confidence,
             "verdict": draft.verdict}, usage)
