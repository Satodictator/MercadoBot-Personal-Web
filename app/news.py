from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import quote_plus

import feedparser
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)
_analyzer = SentimentIntensityAnalyzer()


@dataclass
class NewsResult:
    score: float
    items: list[dict[str, object]]


def fetch_news(query: str, limit: int = 12) -> NewsResult:
    # Google News RSS es una fuente de descubrimiento. El título se analiza, no el artículo completo.
    url = f"https://news.google.com/rss/search?q={quote_plus(query + ' market OR price')}&hl=en-US&gl=US&ceid=US:en"
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "MercadoBotPersonal/0.1"})
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudieron obtener noticias para %s: %s", query, exc)
        return NewsResult(0.0, [])

    items: list[dict[str, object]] = []
    weighted = 0.0
    weight_total = 0.0
    for idx, entry in enumerate(feed.entries[:limit]):
        title = str(getattr(entry, "title", "")).strip()
        if not title:
            continue
        sentiment = float(_analyzer.polarity_scores(title)["compound"])
        weight = 1.0 / (1.0 + idx * 0.15)
        weighted += sentiment * weight
        weight_total += weight
        items.append({
            "title": title,
            "url": str(getattr(entry, "link", "")),
            "sentiment": sentiment,
        })
    score = weighted / weight_total if weight_total else 0.0
    return NewsResult(max(-1.0, min(1.0, score)), items)
