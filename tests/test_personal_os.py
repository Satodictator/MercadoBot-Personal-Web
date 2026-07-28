from datetime import datetime, timedelta, timezone

from app.personal_os import build_countdowns, calculate_goals, calculate_portfolio, compound_projection, scenario_table
from app.private_vault import decrypt_payload, encrypt_payload, generate_key


def test_vault_roundtrip():
    key = generate_key()
    payload = {"journal": [{"id": "x", "type": "BUY", "amount": 100}]}
    token = encrypt_payload(payload, key)
    assert token != str(payload).encode()
    assert decrypt_payload(token, key) == payload


def test_portfolio_average_cost_and_realized_pnl():
    rows = [
        {"id": "d", "type": "DEPOSIT", "amount": 1000},
        {"id": "b1", "type": "BUY", "asset": "AAA", "quantity": 10, "price": 10, "fees": 1},
        {"id": "b2", "type": "BUY", "asset": "AAA", "quantity": 10, "price": 20, "fees": 1},
        {"id": "s1", "type": "SELL", "asset": "AAA", "quantity": 5, "price": 30, "fees": 1},
    ]
    result = calculate_portfolio(rows)
    assert result["journal_count"] == 4
    position = result["open_positions"][0]
    assert position["quantity"] == 15
    assert round(result["realized_pnl"], 2) == 73.5
    assert round(position["cost_basis"], 2) == 226.5


def test_goals_projection_and_scenarios():
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    goals = calculate_goals([{"name": "Meta", "target": 2000, "current": 1000, "target_date": future}], 0)
    assert goals[0]["remaining"] == 1000
    assert goals[0]["required_annualized_return_pct"] > 90
    rows = scenario_table(1000, [-10, 10])
    assert rows[0]["pnl"] == -100
    assert rows[1]["final_value"] == 1100


def test_compound_projection_and_countdown():
    rows = compound_projection(1000, 1, 10, 30, 100, 7)
    assert rows[-1]["balance"] > 1400
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    countdown = build_countdowns([{"name": "Revisión", "target_at": future}])[0]
    assert countdown["status"] == "ACTIVE"
    assert 0 < countdown["seconds_remaining"] <= 300
