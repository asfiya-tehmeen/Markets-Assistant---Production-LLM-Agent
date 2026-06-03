"""get_price tool — current crypto spot price via the CoinGecko Demo API.

Never raises: external failures are returned as ``{"ok": False, "error": ...}`` so the
agent endpoint can degrade gracefully instead of crashing.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

# Friendly ticker -> CoinGecko coin id. Falls back to the raw input if unmapped.
SYMBOL_TO_ID: dict[str, str] = {
    "btc": "bitcoin", "xbt": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ether": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "usdt": "tether", "tether": "tether",
    "usdc": "usd-coin",
    "bnb": "binancecoin",
    "xrp": "ripple", "ripple": "ripple",
    "ada": "cardano", "cardano": "cardano",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "avax": "avalanche-2",
    "dot": "polkadot",
    "matic": "matic-network", "polygon": "matic-network",
    "ltc": "litecoin",
    "link": "chainlink",
}

_COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


def get_price(symbol: str, vs_currency: str = "usd") -> dict:
    """Look up the current price of a crypto asset.

    Args:
        symbol: Ticker or name, e.g. ``"btc"``, ``"ethereum"``.
        vs_currency: Fiat/quote currency, default ``"usd"``.

    Returns:
        On success: ``{"ok": True, "symbol", "price", "change_24h_pct", "source", ...}``.
        On failure: ``{"ok": False, "error": ..., "symbol"}``.
    """
    sym = symbol.strip().lower()
    coin_id = SYMBOL_TO_ID.get(sym, sym)
    vs = vs_currency.strip().lower()

    headers: dict[str, str] = {}
    key = get_settings().coingecko_api_key
    if key:
        headers["x-cg-demo-api-key"] = key

    params = {"ids": coin_id, "vs_currencies": vs, "include_24hr_change": "true"}
    try:
        resp = httpx.get(_COINGECKO_URL, params=params, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # network error, timeout, bad JSON, HTTP error
        return {"ok": False, "error": f"price lookup failed: {exc}", "symbol": symbol}

    if coin_id not in data or vs not in data[coin_id]:
        return {"ok": False, "error": f"unknown symbol '{symbol}' or currency '{vs_currency}'",
                "symbol": symbol}

    entry = data[coin_id]
    return {
        "ok": True,
        "symbol": sym,
        "coin_id": coin_id,
        "vs_currency": vs,
        "price": entry[vs],
        "change_24h_pct": entry.get(f"{vs}_24h_change"),
        "source": "CoinGecko",
    }
