from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import requests


class CryptoMarketError(RuntimeError):
    """Raised when all configured public market-data endpoints fail."""


@dataclass(frozen=True)
class ConversionEdge:
    from_asset: str
    to_asset: str
    symbol: str
    action: str
    rate: float
    capacity_from: float
    spread_bps: float
    quote_volume_24h: float


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _request_json(session: requests.Session, url: str, timeout: float) -> Any:
    response = session.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "MercadoBot-Personal-Web/0.3"},
    )
    response.raise_for_status()
    return response.json()


def fetch_public_spot_snapshot(
    base_urls: Iterable[str],
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Download exchange rules, 24 h statistics and best bid/ask without API keys."""
    client = session or requests.Session()
    errors: list[str] = []
    for raw_base in base_urls:
        base = raw_base.rstrip("/")
        try:
            info = _request_json(client, f"{base}/api/v3/exchangeInfo", timeout)
            tickers = _request_json(client, f"{base}/api/v3/ticker/24hr", timeout)
            books = _request_json(client, f"{base}/api/v3/ticker/bookTicker", timeout)
            pairs = normalize_spot_pairs(info, tickers, books)
            if not pairs:
                raise CryptoMarketError(
                    "el endpoint respondió sin pares spot utilizables"
                )
            return base, pairs
        except Exception as exc:  # noqa: BLE001 - endpoint fallback is intentional
            errors.append(f"{base}: {exc}")
    detail = " | ".join(errors) if errors else "no hay endpoints configurados"
    raise CryptoMarketError(f"No se pudo obtener mercado spot público: {detail}")


def normalize_spot_pairs(
    exchange_info: dict[str, Any],
    tickers: list[dict[str, Any]] | dict[str, Any],
    books: list[dict[str, Any]] | dict[str, Any],
) -> list[dict[str, Any]]:
    """Join exchange metadata, rolling statistics and top-of-book quotes."""
    ticker_rows = tickers if isinstance(tickers, list) else [tickers]
    book_rows = books if isinstance(books, list) else [books]
    ticker_by_symbol = {str(row.get("symbol", "")): row for row in ticker_rows}
    book_by_symbol = {str(row.get("symbol", "")): row for row in book_rows}
    result: list[dict[str, Any]] = []

    for item in exchange_info.get("symbols", []):
        symbol = str(item.get("symbol", "")).upper()
        base_asset = str(item.get("baseAsset", "")).upper()
        quote_asset = str(item.get("quoteAsset", "")).upper()
        status = str(
            item.get("status") or item.get("symbolStatus") or ""
        ).upper()
        spot_allowed = item.get("isSpotTradingAllowed", True)
        if (
            not symbol
            or not base_asset
            or not quote_asset
            or status != "TRADING"
            or spot_allowed is False
        ):
            continue

        ticker = ticker_by_symbol.get(symbol)
        book = book_by_symbol.get(symbol)
        if not ticker or not book:
            continue
        bid = _as_float(book.get("bidPrice"))
        ask = _as_float(book.get("askPrice"))
        if bid <= 0 or ask <= 0 or ask < bid:
            continue
        mid = (bid + ask) / 2
        quote_volume = _as_float(ticker.get("quoteVolume"))
        last_price = _as_float(ticker.get("lastPrice"), mid)
        result.append(
            {
                "symbol": symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "last_price": last_price,
                "bid": bid,
                "ask": ask,
                "bid_qty": _as_float(book.get("bidQty")),
                "ask_qty": _as_float(book.get("askQty")),
                "spread_bps": ((ask - bid) / mid) * 10_000 if mid else 0.0,
                "change_24h_pct": _as_float(ticker.get("priceChangePercent")),
                "base_volume_24h": _as_float(ticker.get("volume")),
                "quote_volume_24h": quote_volume,
                "weighted_avg_price": _as_float(
                    ticker.get("weightedAvgPrice"),
                    last_price,
                ),
                "trade_count_24h": int(_as_float(ticker.get("count"))),
            }
        )

    # Normalize quote volumes to an approximate USD value so BTC/ETH-quoted
    # markets can be compared fairly with stablecoin-quoted markets.
    usd_rates: dict[str, float] = {
        "USD": 1.0,
        "USDT": 1.0,
        "USDC": 1.0,
    }
    ordered = sorted(
        result,
        key=lambda item: item["quote_volume_24h"],
        reverse=True,
    )
    for _ in range(4):
        changed = False
        for row in ordered:
            base = row["base_asset"]
            quote = row["quote_asset"]
            price = _as_float(row["last_price"])
            if quote in usd_rates and price > 0 and base not in usd_rates:
                usd_rates[base] = price * usd_rates[quote]
                changed = True
            elif base in usd_rates and price > 0 and quote not in usd_rates:
                usd_rates[quote] = usd_rates[base] / price
                changed = True
        if not changed:
            break

    for row in result:
        quote_rate = usd_rates.get(row["quote_asset"], 0.0)
        row["quote_usd_rate"] = round(quote_rate, 12)
        row["quote_volume_usd"] = round(
            row["quote_volume_24h"] * quote_rate,
            2,
        )
    return result


def rank_pairs(
    pairs: Iterable[dict[str, Any]],
    *,
    quote_assets: tuple[str, ...] = ("USDT", "USDC", "BTC", "ETH"),
    min_quote_volume: float = 250_000.0,
    max_spread_bps: float = 60.0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Rank liquid pairs while penalising wide spreads and extreme moves."""
    quote_rank = {asset: index for index, asset in enumerate(quote_assets)}
    ranked: list[dict[str, Any]] = []
    for pair in pairs:
        quote = str(pair.get("quote_asset", ""))
        volume = _as_float(pair.get("quote_volume_usd"))
        spread = _as_float(pair.get("spread_bps"), 10_000.0)
        change = abs(_as_float(pair.get("change_24h_pct")))
        if (
            quote not in quote_rank
            or volume < min_quote_volume
            or spread > max_spread_bps
        ):
            continue

        liquidity = min(
            max((math.log10(max(volume, 1.0)) - 5.0) / 5.0, 0.0),
            1.0,
        )
        spread_quality = max(
            0.0,
            1.0 - spread / max(max_spread_bps, 1.0),
        )
        quote_quality = max(0.55, 1.0 - 0.12 * quote_rank[quote])
        movement_quality = min(change / 12.0, 1.0)
        score = 100.0 * (
            0.48 * liquidity
            + 0.30 * spread_quality
            + 0.14 * quote_quality
            + 0.08 * movement_quality
        )

        if score >= 74 and spread <= 12 and volume >= 2_000_000 and change <= 30:
            selection = "PRIORITARIO"
        elif score >= 55 and spread <= 30:
            selection = "VIGILAR"
        else:
            selection = "EVITAR"

        risk_flags: list[str] = []
        if spread > 20:
            risk_flags.append("spread amplio")
        if volume < 1_000_000:
            risk_flags.append("liquidez limitada")
        if change > 25:
            risk_flags.append("movimiento extremo 24 h")
        row = dict(pair)
        row.update(
            {
                "pair_score": round(score, 2),
                "selection": selection,
                "risk_flags": risk_flags,
            }
        )
        ranked.append(row)

    ranked.sort(
        key=lambda row: (
            -row["pair_score"],
            row["spread_bps"],
            -row["quote_volume_usd"],
        )
    )
    return ranked[:limit]


def build_token_prices(
    ranked_pairs: Iterable[dict[str, Any]],
    *,
    stable_quotes: tuple[str, ...] = ("USDT", "USDC"),
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Choose one high-quality stable-quoted market per token."""
    quote_rank = {asset: index for index, asset in enumerate(stable_quotes)}
    chosen: dict[str, dict[str, Any]] = {}
    for pair in ranked_pairs:
        quote = str(pair.get("quote_asset", ""))
        if quote not in quote_rank:
            continue
        base = str(pair.get("base_asset", ""))
        quality = (
            -quote_rank[quote],
            _as_float(pair.get("pair_score")),
            _as_float(pair.get("quote_volume_usd")),
            -_as_float(pair.get("spread_bps")),
        )
        current = chosen.get(base)
        if current is None or quality > current["_quality"]:
            chosen[base] = {
                "_quality": quality,
                "token": base,
                "pair": pair.get("symbol"),
                "quote_asset": quote,
                "price": pair.get("last_price"),
                "bid": pair.get("bid"),
                "ask": pair.get("ask"),
                "spread_bps": round(
                    _as_float(pair.get("spread_bps")),
                    3,
                ),
                "change_24h_pct": round(
                    _as_float(pair.get("change_24h_pct")),
                    4,
                ),
                "quote_volume_24h": round(
                    _as_float(pair.get("quote_volume_24h")),
                    8,
                ),
                "quote_volume_usd": round(
                    _as_float(pair.get("quote_volume_usd")),
                    2,
                ),
                "pair_score": pair.get("pair_score"),
                "selection": pair.get("selection"),
            }
    rows = list(chosen.values())
    rows.sort(
        key=lambda row: (
            -_as_float(row.get("quote_volume_usd")),
            str(row.get("token")),
        )
    )
    for row in rows:
        row.pop("_quality", None)
    return rows[:limit]


def _conversion_edges(
    pairs: Iterable[dict[str, Any]],
    *,
    min_quote_volume: float,
    max_spread_bps: float,
) -> dict[str, list[ConversionEdge]]:
    graph: dict[str, list[ConversionEdge]] = {}
    for pair in pairs:
        spread = _as_float(pair.get("spread_bps"), 10_000.0)
        quote_volume = _as_float(pair.get("quote_volume_usd"))
        if spread > max_spread_bps or quote_volume < min_quote_volume:
            continue
        base = str(pair.get("base_asset", ""))
        quote = str(pair.get("quote_asset", ""))
        symbol = str(pair.get("symbol", ""))
        bid = _as_float(pair.get("bid"))
        ask = _as_float(pair.get("ask"))
        bid_qty = _as_float(pair.get("bid_qty"))
        ask_qty = _as_float(pair.get("ask_qty"))
        if not base or not quote or bid <= 0 or ask <= 0:
            continue
        graph.setdefault(quote, []).append(
            ConversionEdge(
                from_asset=quote,
                to_asset=base,
                symbol=symbol,
                action="COMPRAR",
                rate=1.0 / ask,
                capacity_from=ask * ask_qty,
                spread_bps=spread,
                quote_volume_24h=quote_volume,
            )
        )
        graph.setdefault(base, []).append(
            ConversionEdge(
                from_asset=base,
                to_asset=quote,
                symbol=symbol,
                action="VENDER",
                rate=bid,
                capacity_from=bid_qty,
                spread_bps=spread,
                quote_volume_24h=quote_volume,
            )
        )
    return graph


def find_triangular_arbitrage(
    pairs: Iterable[dict[str, Any]],
    *,
    start_assets: tuple[str, ...] = ("USDT", "USDC"),
    fee_bps: float = 10.0,
    slippage_bps: float = 8.0,
    min_net_bps: float = 12.0,
    min_quote_volume: float = 1_000_000.0,
    max_spread_bps: float = 25.0,
    min_capacity_usd: float = 100.0,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Find three-leg cycles using executable bid/ask prices and conservative costs.

    This is a detector only. A quote can disappear before an order is placed, and
    top-of-book capacity is only an approximation of what could be filled.
    """
    graph = _conversion_edges(
        pairs,
        min_quote_volume=min_quote_volume,
        max_spread_bps=max_spread_bps,
    )
    cost_factor = max(
        0.0,
        1.0 - (fee_bps + slippage_bps) / 10_000.0,
    )
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for start in start_assets:
        for first in graph.get(start, []):
            if first.to_asset == start:
                continue
            for second in graph.get(first.to_asset, []):
                if second.to_asset in {
                    start,
                    first.from_asset,
                    first.to_asset,
                }:
                    continue
                for third in graph.get(second.to_asset, []):
                    if third.to_asset != start:
                        continue
                    if len({first.symbol, second.symbol, third.symbol}) < 3:
                        continue
                    key = (
                        start,
                        first.symbol + first.action,
                        second.symbol + second.action,
                        third.symbol + third.action,
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    edges = (first, second, third)
                    gross_multiplier = math.prod(edge.rate for edge in edges)
                    net_multiplier = math.prod(
                        edge.rate * cost_factor for edge in edges
                    )
                    net_bps = (net_multiplier - 1.0) * 10_000.0
                    if net_bps < min_net_bps:
                        continue

                    cumulative = 1.0
                    max_start = math.inf
                    for edge in edges:
                        if edge.capacity_from <= 0:
                            max_start = 0.0
                            break
                        max_start = min(
                            max_start,
                            edge.capacity_from / max(cumulative, 1e-18),
                        )
                        cumulative *= edge.rate * cost_factor
                    if (
                        not math.isfinite(max_start)
                        or max_start < min_capacity_usd
                    ):
                        continue

                    sample_notional = min(1_000.0, max_start)
                    max_leg_spread = max(edge.spread_bps for edge in edges)
                    status = (
                        "CANDIDATO FUERTE"
                        if net_bps >= max(30.0, min_net_bps * 2)
                        and max_start >= 1_000
                        and max_leg_spread <= 10
                        else "VERIFICAR"
                    )
                    found.append(
                        {
                            "start_asset": start,
                            "route": [
                                start,
                                first.to_asset,
                                second.to_asset,
                                start,
                            ],
                            "gross_edge_pct": round(
                                (gross_multiplier - 1.0) * 100.0,
                                5,
                            ),
                            "net_edge_pct": round(
                                (net_multiplier - 1.0) * 100.0,
                                5,
                            ),
                            "net_edge_bps": round(net_bps, 3),
                            "fee_bps_per_leg": fee_bps,
                            "slippage_bps_per_leg": slippage_bps,
                            "max_start_capacity": round(max_start, 4),
                            "sample_notional": round(sample_notional, 2),
                            "estimated_sample_profit": round(
                                sample_notional * (net_multiplier - 1.0),
                                6,
                            ),
                            "max_leg_spread_bps": round(
                                max_leg_spread,
                                3,
                            ),
                            "status": status,
                            "legs": [
                                {
                                    "pair": edge.symbol,
                                    "action": edge.action,
                                    "from_asset": edge.from_asset,
                                    "to_asset": edge.to_asset,
                                    "rate": round(edge.rate, 12),
                                    "top_book_capacity_from": round(
                                        edge.capacity_from,
                                        8,
                                    ),
                                }
                                for edge in edges
                            ],
                            "warning": (
                                "Solo observación: verificar profundidad, comisiones "
                                "reales, latencia y disponibilidad antes de actuar."
                            ),
                        }
                    )

    found.sort(
        key=lambda row: (
            -row["net_edge_bps"],
            -row["max_start_capacity"],
        )
    )
    return found[:limit]


class CryptoMarketScanner:
    def __init__(
        self,
        settings: Any,
        session: requests.Session | None = None,
    ):
        self.settings = settings
        self.session = session

    def scan(self) -> dict[str, Any]:
        source, pairs = fetch_public_spot_snapshot(
            self.settings.crypto_market_url_list,
            timeout=self.settings.crypto_request_timeout,
            session=self.session,
        )
        ranked = rank_pairs(
            pairs,
            quote_assets=self.settings.crypto_quote_asset_list,
            min_quote_volume=self.settings.crypto_pair_min_volume,
            max_spread_bps=self.settings.crypto_pair_max_spread_bps,
            limit=self.settings.crypto_top_pairs,
        )
        tokens = build_token_prices(
            ranked,
            limit=self.settings.crypto_top_tokens,
        )
        arbitrage = find_triangular_arbitrage(
            pairs,
            start_assets=self.settings.arbitrage_start_asset_list,
            fee_bps=self.settings.arbitrage_fee_bps,
            slippage_bps=self.settings.arbitrage_slippage_bps,
            min_net_bps=self.settings.arbitrage_min_net_bps,
            min_quote_volume=self.settings.arbitrage_min_volume,
            max_spread_bps=self.settings.arbitrage_max_spread_bps,
            min_capacity_usd=self.settings.arbitrage_min_capacity_usd,
            limit=self.settings.arbitrage_top_results,
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "mode": (
                "DATOS PÚBLICOS; DETECCIÓN Y SIMULACIÓN; "
                "SIN EJECUCIÓN DE ÓRDENES"
            ),
            "pairs_seen": len(pairs),
            "selected_pairs": ranked,
            "token_prices": tokens,
            "arbitrage": arbitrage,
            "assumptions": {
                "fee_bps_per_leg": self.settings.arbitrage_fee_bps,
                "slippage_bps_per_leg": self.settings.arbitrage_slippage_bps,
                "min_net_bps": self.settings.arbitrage_min_net_bps,
                "min_capacity_usd": (
                    self.settings.arbitrage_min_capacity_usd
                ),
                "top_of_book_only": True,
            },
        }
