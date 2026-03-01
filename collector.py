"""News collection from RSS feeds and NewsAPI."""

import logging
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from config import (
    DAYS_BACK,
    NEWSAPI_KEY,
    NEWSAPI_QUERIES,
    REQUEST_TIMEOUT,
    RSS_FEEDS,
)

logger = logging.getLogger(__name__)


def _cutoff_date() -> datetime:
    """Return the earliest date we accept articles from."""
    return datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)


def _parse_date(date_str: str | None) -> datetime | None:
    """Try to parse a date string into a timezone-aware datetime."""
    if not date_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def collect_from_rss() -> list[dict]:
    """Fetch articles from configured RSS feeds."""
    articles = []
    cutoff = _cutoff_date()

    for feed_url in RSS_FEEDS:
        try:
            logger.info("Fetching RSS feed: %s", feed_url[:80])
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning("Failed to parse feed: %s", feed_url[:80])
                continue

            for entry in feed.entries:
                url = entry.get("link", "").strip()
                if not url:
                    continue

                title = entry.get("title", "").strip()
                pub_date_str = entry.get("published") or entry.get("updated")
                pub_date = _parse_date(pub_date_str)

                # Skip articles older than our window
                if pub_date and pub_date < cutoff:
                    continue

                articles.append({
                    "title": title,
                    "url": url,
                    "published_date": pub_date.isoformat() if pub_date else None,
                    "source": "rss",
                })

            logger.info("  -> Got %d entries from feed", len(feed.entries))

        except Exception:
            logger.exception("Error fetching RSS feed: %s", feed_url[:80])

    logger.info("Total articles from RSS: %d", len(articles))
    return articles


def collect_from_newsapi() -> list[dict]:
    """Fetch articles from NewsAPI (free tier)."""
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set — skipping NewsAPI collection.")
        return []

    articles = []
    cutoff = _cutoff_date()
    from_date = cutoff.strftime("%Y-%m-%d")

    for query in NEWSAPI_QUERIES:
        try:
            logger.info("NewsAPI query: %s", query)
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 50,
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                logger.warning("NewsAPI error: %s", data.get("message", "unknown"))
                continue

            for item in data.get("articles", []):
                url = item.get("url", "").strip()
                if not url:
                    continue

                pub_date = _parse_date(item.get("publishedAt"))
                articles.append({
                    "title": item.get("title", "").strip(),
                    "url": url,
                    "published_date": pub_date.isoformat() if pub_date else None,
                    "source": "newsapi",
                })

            logger.info("  -> Got %d articles", len(data.get("articles", [])))
            time.sleep(1)  # respect rate limits

        except requests.RequestException:
            logger.exception("NewsAPI request failed for query: %s", query)

    logger.info("Total articles from NewsAPI: %d", len(articles))
    return articles


def collect_all() -> list[dict]:
    """Collect articles from all sources and deduplicate by URL."""
    all_articles = collect_from_rss() + collect_from_newsapi()

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique = []
    for article in all_articles:
        url = article["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    logger.info(
        "Collected %d articles total (%d unique after dedup)",
        len(all_articles),
        len(unique),
    )
    return unique
