"""Unit tests for the deterministic calculator tool."""
from app.tools.calculator import calculate


def test_pnl_long_profit():
    r = calculate("pnl", entry_price=30000, exit_price=35000, quantity=0.5, side="long")
    assert r["ok"] is True
    assert r["pnl"] == 2500.0
    assert r["pnl_pct"] == round(2500 / 15000 * 100, 4)


def test_pnl_short_profit_on_price_drop():
    r = calculate("pnl", entry_price=2000, exit_price=1500, quantity=2, side="short")
    assert r["ok"] is True
    assert r["pnl"] == 1000.0  # short gains when price falls


def test_pnl_long_loss_is_negative():
    r = calculate("pnl", entry_price=100, exit_price=80, quantity=10, side="long")
    assert r["pnl"] == -200.0


def test_pnl_rejects_bad_side():
    r = calculate("pnl", entry_price=100, exit_price=110, quantity=1, side="sideways")
    assert r["ok"] is False


def test_position_size_risk_based():
    # Risk 1% of 50000 = 500; risk/unit = 50 -> 10 units.
    r = calculate("position_size", account_balance=50000, risk_pct=1, entry_price=200,
                  stop_price=150)
    assert r["ok"] is True
    assert r["units"] == 10.0
    assert r["risk_amount"] == 500.0
    assert r["notional"] == 2000.0


def test_position_size_equal_entry_and_stop_errors():
    r = calculate("position_size", account_balance=1000, risk_pct=1, entry_price=100,
                  stop_price=100)
    assert r["ok"] is False


def test_convert_units_to_notional():
    r = calculate("convert", amount=0.25, price=40000, direction="units_to_notional")
    assert r["result"] == 10000.0


def test_convert_notional_to_units():
    r = calculate("convert", amount=10000, price=40000, direction="notional_to_units")
    assert r["result"] == 0.25


def test_convert_zero_price_for_division_errors():
    r = calculate("convert", amount=10, price=0, direction="notional_to_units")
    assert r["ok"] is False


def test_unknown_operation():
    assert calculate("teleport")["ok"] is False


def test_missing_argument_is_clean_error():
    # No exception should escape; missing kwargs become a clean error dict.
    r = calculate("pnl", entry_price=100)
    assert r["ok"] is False
