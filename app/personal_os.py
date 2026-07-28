from __future__ import annotations

import csv
import io
import json
import math
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


TRANSACTION_TYPES = {
    "BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT",
    "FEE", "INCOME", "INTEREST", "DIVIDEND", "STAKING", "ADJUSTMENT",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def merge_payload(template: dict[str, Any], private: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(template))
    for key, value in private.items():
        result[key] = value
    return result


def normalize_journal(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        row = dict(raw)
        tx_type = str(row.get("type", "")).upper().strip()
        if tx_type not in TRANSACTION_TYPES:
            continue
        tx_id = str(row.get("id") or f"manual-{index}")
        if tx_id in seen:
            continue
        seen.add(tx_id)
        quantity = as_float(row.get("quantity"))
        price = as_float(row.get("price"))
        amount = as_float(row.get("amount"))
        if amount == 0 and quantity and price:
            amount = quantity * price
        fees = max(0.0, as_float(row.get("fees")))
        normalized.append({
            "id": tx_id,
            "ts": str(row.get("ts") or utc_now_iso()),
            "type": tx_type,
            "portfolio": str(row.get("portfolio") or "Principal"),
            "account": str(row.get("account") or ""),
            "platform": str(row.get("platform") or ""),
            "asset": str(row.get("asset") or "").upper(),
            "quote_asset": str(row.get("quote_asset") or "USD").upper(),
            "quantity": quantity,
            "price": price,
            "amount": amount,
            "fees": fees,
            "strategy": str(row.get("strategy") or ""),
            "reason_entry": str(row.get("reason_entry") or ""),
            "reason_exit": str(row.get("reason_exit") or ""),
            "rating": str(row.get("rating") or ""),
            "notes": str(row.get("notes") or ""),
            "status": str(row.get("status") or "COMPLETED").upper(),
        })
    normalized.sort(key=lambda item: (item["ts"], item["id"]))
    return normalized


def import_csv_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        for row in csv.DictReader(io.StringIO(text)):
            row["id"] = row.get("id") or f"{path.name}:{len(result)}"
            result.append(dict(row))
    return result


def calculate_portfolio(journal: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = normalize_journal(journal)
    positions: dict[tuple[str, str], dict[str, Any]] = {}
    realized = fees_total = income_total = deposits = withdrawals = 0.0
    closed_trades: list[dict[str, Any]] = []
    for row in rows:
        key = (row["portfolio"], row["asset"])
        position = positions.setdefault(key, {
            "portfolio": row["portfolio"], "asset": row["asset"], "quantity": 0.0,
            "cost_basis": 0.0, "average_cost": 0.0, "realized_pnl": 0.0,
        })
        tx_type, qty, gross, fee = row["type"], max(0.0, row["quantity"]), abs(row["amount"]), row["fees"]
        fees_total += fee
        if tx_type == "BUY" and row["asset"]:
            position["quantity"] += qty
            position["cost_basis"] += gross + fee
            position["average_cost"] = position["cost_basis"] / position["quantity"] if position["quantity"] > 0 else 0.0
        elif tx_type == "SELL" and row["asset"] and qty > 0:
            sold_qty = min(qty, position["quantity"])
            unit_cost = position["cost_basis"] / position["quantity"] if position["quantity"] > 0 else 0.0
            allocated_cost = unit_cost * sold_qty
            proceeds = gross - fee
            pnl = proceeds - allocated_cost
            position["quantity"] -= sold_qty
            position["cost_basis"] = max(0.0, position["cost_basis"] - allocated_cost)
            position["average_cost"] = position["cost_basis"] / position["quantity"] if position["quantity"] > 0 else 0.0
            position["realized_pnl"] += pnl
            realized += pnl
            closed_trades.append({
                "id": row["id"], "ts": row["ts"], "portfolio": row["portfolio"],
                "asset": row["asset"], "strategy": row["strategy"], "quantity": sold_qty,
                "proceeds": round(proceeds, 8), "cost_basis": round(allocated_cost, 8),
                "net_pnl": round(pnl, 8),
                "return_pct": round((pnl / allocated_cost * 100) if allocated_cost else 0.0, 6),
                "fees": fee, "rating": row["rating"], "reason_exit": row["reason_exit"],
            })
        elif tx_type in {"INCOME", "INTEREST", "DIVIDEND", "STAKING"}:
            net = gross - fee
            income_total += net
            realized += net
        elif tx_type == "FEE":
            realized -= gross + fee
        elif tx_type in {"DEPOSIT", "TRANSFER_IN"}:
            deposits += gross
        elif tx_type in {"WITHDRAWAL", "TRANSFER_OUT"}:
            withdrawals += gross
    open_positions = [{
        **value,
        "quantity": round(value["quantity"], 12),
        "cost_basis": round(value["cost_basis"], 8),
        "average_cost": round(value["average_cost"], 12),
        "realized_pnl": round(value["realized_pnl"], 8),
    } for value in positions.values() if value["quantity"] > 1e-12]
    by_strategy: dict[str, dict[str, Any]] = defaultdict(lambda: {"operations": 0, "net_pnl": 0.0, "wins": 0, "losses": 0})
    for trade in closed_trades:
        bucket = by_strategy[trade["strategy"] or "Sin estrategia"]
        bucket["operations"] += 1
        bucket["net_pnl"] += trade["net_pnl"]
        bucket["wins"] += int(trade["net_pnl"] > 0)
        bucket["losses"] += int(trade["net_pnl"] < 0)
    strategy_stats = [{
        "strategy": name, **bucket, "net_pnl": round(bucket["net_pnl"], 8),
        "win_rate": round(bucket["wins"] / bucket["operations"], 6) if bucket["operations"] else 0.0,
    } for name, bucket in by_strategy.items()]
    strategy_stats.sort(key=lambda item: (-item["net_pnl"], -item["win_rate"]))
    return {
        "journal_count": len(rows), "open_positions": open_positions,
        "closed_trades": list(reversed(closed_trades[-500:])), "realized_pnl": round(realized, 8),
        "income_total": round(income_total, 8), "fees_total": round(fees_total, 8),
        "deposits": round(deposits, 8), "withdrawals": round(withdrawals, 8),
        "net_contributions": round(deposits - withdrawals, 8),
        "invested_cost": round(sum(item["cost_basis"] for item in open_positions), 8),
        "strategy_stats": strategy_stats,
    }


def calculate_goals(goals: Iterable[dict[str, Any]], current_capital: float) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for raw in goals:
        target = max(0.0, as_float(raw.get("target")))
        current = max(0.0, as_float(raw.get("current"), current_capital))
        target_date = str(raw.get("target_date") or "")
        remaining, days = max(0.0, target - current), 0
        if target_date:
            try:
                end = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                if end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
                days = max(0, (end - datetime.now(timezone.utc)).days)
            except ValueError:
                days = 0
        monthly_required = remaining / max(days / 30.4375, 1.0) if remaining else 0.0
        required_return = (((target / current) ** (365 / max(days, 1)) - 1) * 100
                           if current > 0 and target > current and days > 0 else 0.0)
        output.append({
            "id": str(raw.get("id") or f"goal-{len(output)+1}"), "name": str(raw.get("name") or "Meta"),
            "target": round(target, 2), "current": round(current, 2), "remaining": round(remaining, 2),
            "progress": round(min(current / target, 1.0), 6) if target else 0.0,
            "target_date": target_date, "days_remaining": days,
            "monthly_contribution_required": round(monthly_required, 2),
            "required_annualized_return_pct": round(required_return, 4),
            "status": "COMPLETADA" if target and current >= target else "ACTIVA",
        })
    return output


def compound_projection(initial: float, cycle_return_pct: float, cycle_days: float, days: int,
                        periodic_contribution: float = 0.0, contribution_every_days: int = 7) -> list[dict[str, Any]]:
    initial, rate, cycle_days = max(0.0, initial), cycle_return_pct / 100.0, max(1.0, cycle_days)
    contribution_every_days = max(1, contribution_every_days)
    balance, total_contributed, rows = initial, initial, []
    for day in range(0, max(0, days) + 1):
        if day and day % contribution_every_days == 0:
            balance += periodic_contribution; total_contributed += periodic_contribution
        if day and day % round(cycle_days) == 0: balance *= 1 + rate
        if day in {0, 7, 30, 90, 180, 365, days}:
            rows.append({"day": day, "balance": round(balance, 2), "contributed": round(total_contributed, 2),
                         "projected_profit": round(balance - total_contributed, 2)})
    return [dict((row["day"], row) for row in rows)[key] for key in sorted(dict((row["day"], row) for row in rows))]


def scenario_table(notional: float, percentages: Iterable[float]) -> list[dict[str, Any]]:
    return [{"change_pct": pct, "final_value": round(notional * (1 + pct / 100), 2),
             "pnl": round(notional * pct / 100, 2)} for pct in percentages]


def build_capital_lots(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    now, output = datetime.now(timezone.utc), []
    for raw in rows:
        available_at, seconds = str(raw.get("available_at") or ""), None
        if available_at:
            try:
                parsed = datetime.fromisoformat(available_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
                seconds = max(0, int((parsed - now).total_seconds()))
            except ValueError: seconds = None
        output.append({
            "id": str(raw.get("id") or f"lot-{len(output)+1}"), "name": str(raw.get("name") or "Lote"),
            "amount": round(as_float(raw.get("amount")), 2), "currency": str(raw.get("currency") or "USD").upper(),
            "location": str(raw.get("location") or ""), "status": str(raw.get("status") or "AVAILABLE").upper(),
            "entered_at": str(raw.get("entered_at") or ""), "available_at": available_at,
            "seconds_remaining": seconds, "strategy": str(raw.get("strategy") or ""), "notes": str(raw.get("notes") or ""),
        })
    return output


def build_countdowns(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    now, output = datetime.now(timezone.utc), []
    for raw in rows:
        target, seconds, status = str(raw.get("target_at") or ""), None, str(raw.get("status") or "ACTIVE").upper()
        if target:
            try:
                parsed = datetime.fromisoformat(target.replace("Z", "+00:00"))
                if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
                seconds = int((parsed - now).total_seconds())
                if seconds <= 0 and status == "ACTIVE": status = "DUE"
                seconds = max(0, seconds)
            except ValueError: seconds = None
        output.append({
            "id": str(raw.get("id") or f"countdown-{len(output)+1}"), "name": str(raw.get("name") or "Cuenta regresiva"),
            "target_at": target, "seconds_remaining": seconds, "status": status,
            "linked_type": str(raw.get("linked_type") or ""), "linked_id": str(raw.get("linked_id") or ""),
            "action": str(raw.get("action") or ""),
        })
    return output


SESSION_DEFINITIONS = [
    {"name": "Tokio", "tz": "Asia/Tokyo", "open": "09:00", "close": "15:00"},
    {"name": "Hong Kong", "tz": "Asia/Hong_Kong", "open": "09:30", "close": "16:00"},
    {"name": "Londres", "tz": "Europe/London", "open": "08:00", "close": "16:30"},
    {"name": "Nueva York", "tz": "America/New_York", "open": "09:30", "close": "16:00"},
    {"name": "Chicago", "tz": "America/Chicago", "open": "08:30", "close": "15:00"},
    {"name": "Sídney", "tz": "Australia/Sydney", "open": "10:00", "close": "16:00"},
]


def _parse_hhmm(value: str) -> time:
    hour, minute = [int(part) for part in value.split(":", 1)]
    return time(hour, minute)


def market_sessions(user_timezone: str = "America/Detroit") -> list[dict[str, Any]]:
    now_utc, user_tz, result = datetime.now(timezone.utc), ZoneInfo(user_timezone), []
    for definition in SESSION_DEFINITIONS:
        zone, local_now = ZoneInfo(definition["tz"]), now_utc.astimezone(ZoneInfo(definition["tz"]))
        open_time, close_time = _parse_hhmm(definition["open"]), _parse_hhmm(definition["close"])
        is_open = local_now.weekday() < 5 and open_time <= local_now.time().replace(tzinfo=None) < close_time
        open_dt = datetime.combine(local_now.date(), open_time, zone)
        close_dt = datetime.combine(local_now.date(), close_time, zone)
        if local_now.weekday() >= 5 or local_now >= close_dt:
            days = 1
            while local_now.date().fromordinal(local_now.date().toordinal() + days).weekday() >= 5: days += 1
            open_dt = datetime.combine(local_now.date().fromordinal(local_now.date().toordinal() + days), open_time, zone)
        next_event = close_dt if is_open else open_dt
        result.append({
            "name": definition["name"], "timezone": definition["tz"], "local_time": local_now.isoformat(),
            "user_time": local_now.astimezone(user_tz).isoformat(), "status": "ABIERTO" if is_open else "CERRADO",
            "next_event": "CIERRE" if is_open else "APERTURA", "next_event_at": next_event.astimezone(timezone.utc).isoformat(),
            "seconds_remaining": max(0, int((next_event.astimezone(timezone.utc) - now_utc).total_seconds())),
        })
    return result


def feature_registry() -> list[dict[str, Any]]:
    groups = [
        ("Panel y portafolios", "ACTIVE", "Resumen, capital por categorías, posiciones, metas y resultados."),
        ("Memoria y diario", "ACTIVE", "Vault cifrado, diario normalizado, estrategias, motivos y resultados."),
        ("Precios y señales", "ACTIVE", "Mercados multiactivo, tokens, noticias, modelos y selección de pares."),
        ("Arbitraje triangular", "ACTIVE", "Detector informativo con bid/ask, costes y capacidad visible."),
        ("Arbitraje entre plataformas", "PREPARED", "Requiere feeds comparables, saldos, comisiones y latencia por plataforma."),
        ("Spot-futuros y financiación", "PREPARED", "Requiere conectores de derivados y financiación autorizados."),
        ("Opciones y futuros", "PREPARED", "Requiere cadenas, griegas, vencimientos y licencias de datos."),
        ("Fundamentales", "PREPARED", "Requiere proveedor de estados financieros y calendario corporativo."),
        ("On-chain y ballenas", "PREPARED", "Requiere proveedor on-chain y reglas contra falsos positivos."),
        ("Calendario y horarios", "ACTIVE", "Sesiones con zonas horarias, DST, eventos y cuentas regresivas."),
        ("Estrategias y versiones", "ACTIVE", "Biblioteca, parámetros, compatibilidad y resultados personales."),
        ("Backtesting y replay", "ACTIVE", "Arquitectura y pruebas históricas; replay avanzado preparado."),
        ("Importación y conciliación", "ACTIVE", "CSV genérico, deduplicación y revisión sin alterar originales."),
        ("Reportes", "ACTIVE", "JSON y CSV generados; PDF y hojas avanzadas preparados."),
        ("Órdenes inteligentes", "LOCKED", "Bloqueadas en web pública. Solo manual o paper con autorización explícita."),
        ("Ejecución automática real", "LOCKED", "Requiere servidor privado, controles, credenciales y aprobación."),
        ("Asistente conversacional", "PREPARED", "Necesita backend privado autenticado para escribir memoria."),
        ("Sincronización privada", "PREPARED", "Vault cifrado activo; panel autenticado requiere hosting adicional."),
    ]
    return [{"feature": name, "status": status, "detail": detail} for name, status, detail in groups]


def build_public_personal_center(payload: dict[str, Any], *, publish_private_summary: bool = False,
                                 user_timezone: str = "America/Detroit") -> dict[str, Any]:
    journal = normalize_journal(payload.get("journal", []))
    portfolio = calculate_portfolio(journal)
    profile = payload.get("profile", {}) if isinstance(payload.get("profile", {}), dict) else {}
    portfolios = payload.get("portfolios", []) if isinstance(payload.get("portfolios", []), list) else []
    goals = calculate_goals(payload.get("goals", []), portfolio["net_contributions"] + portfolio["realized_pnl"])
    capital_lots, countdowns = build_capital_lots(payload.get("capital_lots", [])), build_countdowns(payload.get("countdowns", []))
    execution_policy = payload.get("execution_policy", {})
    public: dict[str, Any] = {
        "configured": bool(payload), "privacy_mode": "PRIVATE_NOT_PUBLISHED" if not publish_private_summary else "AGGREGATES_PUBLISHED",
        "generated_at": utc_now_iso(), "profile_name": str(profile.get("display_name") or "Perfil personal"),
        "base_currency": str(profile.get("base_currency") or "USD"), "user_timezone": user_timezone,
        "execution_policy": {"mode": str(execution_policy.get("mode") or "DISABLED").upper(),
            "real_orders_enabled": bool(execution_policy.get("real_orders_enabled", False)),
            "manual_approval_required": bool(execution_policy.get("manual_approval_required", True)),
            "allowed_markets": execution_policy.get("allowed_markets", [])},
        "sessions": market_sessions(user_timezone), "features": feature_registry(),
        "strategy_catalog": payload.get("strategies", []),
        "scenario_defaults": scenario_table(1000.0, [-10, -5, -3, -1, 1, 3, 5, 10]),
    }
    if not publish_private_summary:
        public.update({"dashboard": {}, "portfolios": [], "journal": [], "closed_trades": [], "open_positions": [],
                       "strategy_stats": [], "goals": [], "capital_lots": [], "countdowns": [], "calendar_events": []})
        return public
    available = sum(item["amount"] for item in capital_lots if item["status"] in {"AVAILABLE", "RESERVE"})
    reserved = sum(item["amount"] for item in capital_lots if item["status"] == "RESERVE")
    in_transfer = sum(item["amount"] for item in capital_lots if item["status"] in {"TRANSFER", "MATURING", "WITHDRAWING"})
    public.update({
        "dashboard": {"capital_available": round(available, 2), "capital_invested_cost": portfolio["invested_cost"],
            "capital_reserved": round(reserved, 2), "capital_in_transfer": round(in_transfer, 2),
            "realized_pnl": portfolio["realized_pnl"], "fees_total": portfolio["fees_total"],
            "open_positions": len(portfolio["open_positions"]), "closed_operations": len(portfolio["closed_trades"]),
            "journal_count": portfolio["journal_count"], "portfolios": len(portfolios)},
        "portfolios": portfolios, "journal": list(reversed(journal[-500:])), "closed_trades": portfolio["closed_trades"],
        "open_positions": portfolio["open_positions"], "strategy_stats": portfolio["strategy_stats"], "goals": goals,
        "capital_lots": capital_lots, "countdowns": countdowns, "calendar_events": payload.get("calendar_events", []),
    })
    return public
