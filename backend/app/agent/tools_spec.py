"""OpenAI-format tool schemas exposed to the router, plus a name->function dispatcher."""
from __future__ import annotations

from typing import Any

from app.cache import get_price_cached
from app.tools.calculator import calculate
from app.tools.knowledge_base import search_knowledge_base

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the finance/markets knowledge base for definitions, FAQ, and "
                           "regulatory concepts. Use for 'what is', 'explain', 'how does X work' "
                           "questions about markets, trading, crypto, and regulation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "n_results": {"type": "integer", "description": "How many chunks to return.",
                                  "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Get the current market price of a cryptocurrency (e.g. BTC, ETH, SOL). "
                           "Use whenever the user asks for a live or current price/value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Ticker or name, e.g. 'btc'."},
                    "vs_currency": {"type": "string", "description": "Quote currency.",
                                    "default": "usd"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Deterministic finance math. Use for profit/loss, position sizing, or "
                           "unit<->notional conversions. Do not do this math yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["pnl", "position_size", "convert"]},
                    "entry_price": {"type": "number"},
                    "exit_price": {"type": "number"},
                    "quantity": {"type": "number"},
                    "side": {"type": "string", "enum": ["long", "short"]},
                    "account_balance": {"type": "number"},
                    "risk_pct": {"type": "number"},
                    "stop_price": {"type": "number"},
                    "amount": {"type": "number"},
                    "price": {"type": "number"},
                    "direction": {"type": "string",
                                  "enum": ["units_to_notional", "notional_to_units"]},
                },
                "required": ["operation"],
            },
        },
    },
]

_DISPATCH = {
    "search_knowledge_base": search_knowledge_base,
    "get_price": get_price_cached,  # Redis-cached wrapper around the raw CoinGecko call
    "calculate": calculate,
}


def dispatch_tool(name: str, args: dict[str, Any]) -> dict:
    """Execute a tool by name with kwargs. Never raises; errors come back as a dict."""
    func = _DISPATCH.get(name)
    if func is None:
        return {"ok": False, "error": f"unknown tool '{name}'"}
    try:
        return func(**args)
    except Exception as exc:  # bad/missing args from the model
        return {"ok": False, "error": f"tool '{name}' failed: {exc}"}
