"""calculate tool — deterministic finance math. No LLM, no network.

Supported operations:
  - ``pnl``: profit/loss of a closed trade.
  - ``position_size``: units to buy given account risk and a stop.
  - ``convert``: units<->notional via a price.

All operations validate their inputs and return ``{"ok": False, "error": ...}`` on bad input
rather than raising, so the agent can surface a clean message.
"""
from __future__ import annotations


def calculate(operation: str, **params: float | str) -> dict:
    """Dispatch a deterministic calculation.

    Args:
        operation: One of ``"pnl"``, ``"position_size"``, ``"convert"``.
        **params: Operation-specific numeric arguments (see helpers below).
    """
    op = str(operation).strip().lower()
    try:
        if op == "pnl":
            return _pnl(**params)
        if op == "position_size":
            return _position_size(**params)
        if op == "convert":
            return _convert(**params)
        return {"ok": False, "error": f"unknown operation '{operation}'"}
    except TypeError as exc:
        return {"ok": False, "error": f"missing or extra argument for '{op}': {exc}"}
    except (ValueError, ZeroDivisionError) as exc:
        return {"ok": False, "error": f"invalid input for '{op}': {exc}"}


def _pnl(entry_price: float, exit_price: float, quantity: float, side: str = "long") -> dict:
    """Profit/loss for a closed position. ``side`` is 'long' or 'short'."""
    entry_price, exit_price, quantity = float(entry_price), float(exit_price), float(quantity)
    side = str(side).lower()
    if side not in ("long", "short"):
        return {"ok": False, "error": "side must be 'long' or 'short'"}
    direction = 1 if side == "long" else -1
    pnl = (exit_price - entry_price) * quantity * direction
    cost_basis = entry_price * quantity
    pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0
    return {
        "ok": True, "operation": "pnl", "side": side,
        "entry_price": entry_price, "exit_price": exit_price, "quantity": quantity,
        "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 4),
    }


def _position_size(account_balance: float, risk_pct: float, entry_price: float,
                   stop_price: float) -> dict:
    """Position size (units) so that hitting the stop loses ``risk_pct`` of the account."""
    account_balance, risk_pct = float(account_balance), float(risk_pct)
    entry_price, stop_price = float(entry_price), float(stop_price)
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0:
        return {"ok": False, "error": "entry_price and stop_price must differ"}
    risk_amount = account_balance * (risk_pct / 100.0)
    units = risk_amount / risk_per_unit
    return {
        "ok": True, "operation": "position_size",
        "account_balance": account_balance, "risk_pct": risk_pct,
        "entry_price": entry_price, "stop_price": stop_price,
        "risk_amount": round(risk_amount, 2), "risk_per_unit": round(risk_per_unit, 8),
        "units": round(units, 8), "notional": round(units * entry_price, 2),
    }


def _convert(amount: float, price: float, direction: str = "units_to_notional") -> dict:
    """Convert between units and notional value via a price."""
    amount, price = float(amount), float(price)
    direction = str(direction).lower()
    if direction == "units_to_notional":
        result = amount * price
    elif direction == "notional_to_units":
        if price == 0:
            return {"ok": False, "error": "price must be non-zero"}
        result = amount / price
    else:
        return {"ok": False, "error": "direction must be 'units_to_notional' or 'notional_to_units'"}
    return {"ok": True, "operation": "convert", "direction": direction,
            "amount": amount, "price": price, "result": round(result, 8)}
