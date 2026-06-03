"""LangGraph agent: router (LLM + tools) -> tool execution loop -> structured synthesis.

Flow:
    agent  --(tool calls?)--> tools --> agent  ... (bounded) ... --> synthesize --> END

The agent node lets the LLM decide which tools to call; the tools node runs them and feeds
results back; once the LLM stops requesting tools (or the loop cap is hit), synthesis produces
the final grounded JSON. The whole run is wrapped so the endpoint never crashes.
"""
from __future__ import annotations

import json
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.llm import LLMClient
from app.agent.synthesize import synthesize_response
from app.agent.tools_spec import TOOL_SCHEMAS, dispatch_tool
from app.observability import observe_run

MAX_TOOL_ITERATIONS = 3

_ROUTER_SYSTEM = (
    "You are Markets Assistant's router. Decide which tools to call to gather what's needed to "
    "answer the user's finance/markets question. Use search_knowledge_base for concepts, "
    "definitions, and regulatory questions; get_price for current crypto prices; calculate for "
    "P/L, position sizing, and conversions. You may call several tools, including in parallel. "
    "If the question is out of scope (not finance/markets) or asks for personalized investment "
    "advice, you may answer without tools. Once you have enough information, stop calling tools."
)


class AgentState(TypedDict):
    """Mutable state threaded through the graph."""

    question: str
    messages: list[dict[str, Any]]
    tool_outputs: list[dict]
    retrieval_weak: bool
    iterations: int
    prompt_tokens: int
    completion_tokens: int
    response: dict


_llm = LLMClient()


def _agent_node(state: AgentState) -> AgentState:
    """Ask the LLM what to do next (call tools or finish)."""
    resp = _llm.chat(messages=state["messages"], tools=TOOL_SCHEMAS, tool_choice="auto")
    state["prompt_tokens"] += resp.usage.prompt_tokens
    state["completion_tokens"] += resp.usage.completion_tokens
    msg = resp.choices[0].message
    state["messages"].append(msg.model_dump(exclude_none=True))
    return state


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if last.get("tool_calls") and state["iterations"] < MAX_TOOL_ITERATIONS:
        return "tools"
    return "synthesize"


def _tools_node(state: AgentState) -> AgentState:
    """Execute every tool call from the last assistant message and append the results."""
    last = state["messages"][-1]
    for call in last.get("tool_calls", []):
        name = call["function"]["name"]
        try:
            args = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        result = dispatch_tool(name, args)
        state["tool_outputs"].append({"tool": name, "args": args, "result": result})
        if name == "search_knowledge_base" and result.get("ok"):
            state["retrieval_weak"] = bool(result.get("weak"))
        state["messages"].append({
            "role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, default=str),
        })
    state["iterations"] += 1
    return state


def _synthesize_node(state: AgentState) -> AgentState:
    response, usage = synthesize_response(_llm, state)
    state["prompt_tokens"] += usage["prompt_tokens"]
    state["completion_tokens"] += usage["completion_tokens"]
    state["response"] = response
    return state


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", _tools_node)
    graph.add_node("synthesize", _synthesize_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue,
                                {"tools": "tools", "synthesize": "synthesize"})
    graph.add_edge("tools", "agent")
    graph.add_edge("synthesize", END)
    return graph.compile()


_COMPILED = _build_graph()


def run_agent(question: str) -> dict:
    """Run the agent end-to-end. Returns the structured response plus a ``meta`` block.

    Never raises: any unexpected failure degrades to a NEEDS_HUMAN response.
    """
    started = time.perf_counter()
    initial: AgentState = {
        "question": question,
        "messages": [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user", "content": question},
        ],
        "tool_outputs": [],
        "retrieval_weak": False,
        "iterations": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "response": {},
    }
    tool_outputs: list[dict] = []
    try:
        final = _COMPILED.invoke(initial)
        response = final["response"]
        tool_outputs = final["tool_outputs"]
        prompt_tokens = final["prompt_tokens"]
        completion_tokens = final["completion_tokens"]
    except Exception as exc:
        response = {
            "answer": f"The assistant encountered an internal error and is escalating ({exc}).",
            "sources": [], "confidence": "low", "verdict": "NEEDS_HUMAN",
        }
        prompt_tokens, completion_tokens = 0, 0

    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    tokens = {"prompt": prompt_tokens, "completion": completion_tokens,
              "total": prompt_tokens + completion_tokens}
    response["meta"] = {
        "tools_called": [o["tool"] for o in tool_outputs],
        "latency_ms": latency_ms,
        "model": _llm.model,
        "tokens": tokens,
    }

    observe_run(question=question, response=response, tool_outputs=tool_outputs,
                tokens=tokens, latency_ms=latency_ms, model=_llm.model)
    return response
