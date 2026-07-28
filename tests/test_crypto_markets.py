from app.crypto_markets import (
    build_token_prices,
    find_triangular_arbitrage,
    normalize_spot_pairs,
    rank_pairs,
)


def test_normalize_and_rank_pairs():
    info = {
        "symbols": [
            {
                "symbol": "AAAUSDT",
                "baseAsset": "AAA",
                "quoteAsset": "USDT",
                "status": "TRADING",
            },
            {
                "symbol": "BADUSDT",
                "baseAsset": "BAD",
                "quoteAsset": "USDT",
                "status": "HALT",
            },
            {
                "symbol": "CCCBTC",
                "baseAsset": "CCC",
                "quoteAsset": "BTC",
                "status": "TRADING",
            },
            {
                "symbol": "BTCUSDT",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
            },
        ]
    }
    tickers = [
        {
            "symbol": "AAAUSDT",
            "lastPrice": "10",
            "quoteVolume": "5000000",
            "volume": "500000",
            "priceChangePercent": "4",
            "count": 1000,
        },
        {
            "symbol": "BADUSDT",
            "lastPrice": "1",
            "quoteVolume": "9999999",
        },
        {
            "symbol": "CCCBTC",
            "lastPrice": "0.001",
            "quoteVolume": "100",
            "volume": "100000",
            "priceChangePercent": "2",
        },
        {
            "symbol": "BTCUSDT",
            "lastPrice": "60000",
            "quoteVolume": "100000000",
            "volume": "1666",
            "priceChangePercent": "1",
        },
    ]
    books = [
        {
            "symbol": "AAAUSDT",
            "bidPrice": "9.99",
            "askPrice": "10.01",
            "bidQty": "1000",
            "askQty": "1000",
        },
        {
            "symbol": "BADUSDT",
            "bidPrice": "1",
            "askPrice": "1.01",
            "bidQty": "1",
            "askQty": "1",
        },
        {
            "symbol": "CCCBTC",
            "bidPrice": "0.000999",
            "askPrice": "0.001001",
            "bidQty": "100000",
            "askQty": "100000",
        },
        {
            "symbol": "BTCUSDT",
            "bidPrice": "59999",
            "askPrice": "60001",
            "bidQty": "10",
            "askQty": "10",
        },
    ]
    pairs = normalize_spot_pairs(info, tickers, books)
    assert len(pairs) == 3
    ranked = rank_pairs(
        pairs,
        min_quote_volume=100_000,
        max_spread_bps=50,
    )
    assert ranked[0]["pair_score"] > 0
    assert any(row["symbol"] == "CCCBTC" for row in ranked)
    ccc = next(row for row in pairs if row["symbol"] == "CCCBTC")
    assert ccc["quote_volume_usd"] == 6_000_000.0
    tokens = build_token_prices(ranked)
    aaa = next(row for row in tokens if row["token"] == "AAA")
    assert aaa["price"] == 10.0


def test_triangular_arbitrage_uses_bid_ask_and_costs():
    pairs = [
        {
            "symbol": "AAAUSDT",
            "base_asset": "AAA",
            "quote_asset": "USDT",
            "bid": 1.99,
            "ask": 2.0,
            "bid_qty": 10000,
            "ask_qty": 10000,
            "spread_bps": 10,
            "quote_volume_24h": 50_000_000,
            "quote_volume_usd": 50_000_000,
        },
        {
            "symbol": "AAABBB",
            "base_asset": "AAA",
            "quote_asset": "BBB",
            "bid": 4.0,
            "ask": 4.01,
            "bid_qty": 10000,
            "ask_qty": 10000,
            "spread_bps": 10,
            "quote_volume_24h": 50_000_000,
            "quote_volume_usd": 50_000_000,
        },
        {
            "symbol": "BBBUSDT",
            "base_asset": "BBB",
            "quote_asset": "USDT",
            "bid": 0.255,
            "ask": 0.256,
            "bid_qty": 100000,
            "ask_qty": 100000,
            "spread_bps": 10,
            "quote_volume_24h": 50_000_000,
            "quote_volume_usd": 50_000_000,
        },
    ]
    rows = find_triangular_arbitrage(
        pairs,
        fee_bps=1,
        slippage_bps=1,
        min_net_bps=1,
        min_quote_volume=1,
        max_spread_bps=100,
        min_capacity_usd=1,
    )
    assert rows
    best = rows[0]
    assert best["route"][0] == "USDT"
    assert best["route"][-1] == "USDT"
    assert best["net_edge_bps"] > 0
    assert len(best["legs"]) == 3


def test_arbitrage_rejects_edge_after_costs():
    pairs = [
        {
            "symbol": "AAAUSDT",
            "base_asset": "AAA",
            "quote_asset": "USDT",
            "bid": 1,
            "ask": 1,
            "bid_qty": 1000,
            "ask_qty": 1000,
            "spread_bps": 0,
            "quote_volume_24h": 10_000_000,
            "quote_volume_usd": 10_000_000,
        },
        {
            "symbol": "AAABBB",
            "base_asset": "AAA",
            "quote_asset": "BBB",
            "bid": 1,
            "ask": 1,
            "bid_qty": 1000,
            "ask_qty": 1000,
            "spread_bps": 0,
            "quote_volume_24h": 10_000_000,
            "quote_volume_usd": 10_000_000,
        },
        {
            "symbol": "BBBUSDT",
            "base_asset": "BBB",
            "quote_asset": "USDT",
            "bid": 1.0002,
            "ask": 1.0003,
            "bid_qty": 1000,
            "ask_qty": 1000,
            "spread_bps": 1,
            "quote_volume_24h": 10_000_000,
            "quote_volume_usd": 10_000_000,
        },
    ]
    assert find_triangular_arbitrage(
        pairs,
        fee_bps=10,
        slippage_bps=5,
        min_net_bps=1,
        min_quote_volume=1,
        min_capacity_usd=1,
    ) == []
