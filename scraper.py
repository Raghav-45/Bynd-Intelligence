"""Article scraping — extract full text from article URLs."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import trafilatura
from bs4 import BeautifulSoup

from config import MAX_RETRIES, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

MAX_WORKERS = 10

_session_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
}

# Sites that block scrapers (paywalled / bot-detection). Skip immediately.
BLOCKED_DOMAINS = {
    "nytimes.com", "wsj.com", "bloomberg.com", "reuters.com",
    "axios.com", "politico.com", "seekingalpha.com", "thestreet.com",
    "japantimes.co.jp", "investing.com", "washingtonpost.com",
    "ft.com", "barrons.com", "breakingdefense.com", "ndtv.com",
    "thehill.com", "wionews.com",
}


def _resolve_google_news_url(url: str) -> str:
    """Decode a Google News redirect URL to the real article URL.

    Google News uses JavaScript redirects. We replicate the internal
    batchexecute POST request to extract the real article URL.
    """
    if "news.google.com" not in url:
        return url

    try:
        # Step 1: Fetch the Google News article page to get the data-p payload
        resp = requests.get(url, headers=_session_headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.select_one("c-wiz[data-p]")
        if not tag:
            logger.debug("No c-wiz[data-p] found for: %s", url[:60])
            return url

        data_p = tag.get("data-p")
        obj = json.loads(data_p.replace("%.@.", '["garturlreq",'))

        # Step 2: POST to batchexecute to get the decoded URL
        payload = {
            "f.req": json.dumps(
                [[["Fbv4je", json.dumps(obj[:-6] + obj[-2:]), "null", "generic"]]]
            )
        }
        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "user-agent": _session_headers["User-Agent"],
        }
        resp2 = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            headers=headers,
            data=payload,
            timeout=REQUEST_TIMEOUT,
        )
        array_string = json.loads(resp2.text.replace(")]}'", ""))[0][2]
        article_url = json.loads(array_string)[1]

        if article_url:
            return article_url

    except Exception as exc:
        logger.debug("Failed to decode Google News URL: %s (%s)", url[:60], exc)

    return url


def _is_blocked_domain(url: str) -> bool:
    """Check if the URL belongs to a known paywalled/bot-blocking site."""
    from urllib.parse import urlparse

    hostname = urlparse(url).hostname or ""
    return any(hostname == d or hostname.endswith("." + d) for d in BLOCKED_DOMAINS)


def scrape_article(url: str) -> tuple[str | None, str]:
    """Download a URL and extract the main article text.

    Returns (extracted_text, resolved_url).
    """
    resolved = _resolve_google_news_url(url)

    if _is_blocked_domain(resolved):
        logger.debug("Skipping blocked domain: %s", resolved[:80])
        return None, resolved

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                resolved,
                timeout=REQUEST_TIMEOUT,
                headers=_session_headers,
            )
            resp.raise_for_status()

            text = trafilatura.extract(resp.text)
            if text and len(text.strip()) > 50:
                return text.strip(), resolved

            logger.warning("Extraction returned little/no text: %s", resolved[:80])
            return None, resolved

        except requests.Timeout:
            logger.warning(
                "Timeout (attempt %d/%d): %s", attempt, MAX_RETRIES, resolved[:80]
            )
        except requests.RequestException as exc:
            logger.warning(
                "Request error (attempt %d/%d) for %s: %s",
                attempt, MAX_RETRIES, resolved[:80], exc,
            )

        if attempt < MAX_RETRIES:
            time.sleep(2)

    logger.error("Failed to scrape after %d attempts: %s", MAX_RETRIES, resolved[:80])
    return None, resolved


def scrape_articles(articles: list[dict]) -> list[dict]:
    """Scrape full text for a list of articles using a thread pool.

    Adds 'full_text' key to each article dict. Articles where scraping fails
    get full_text=None but are kept (they can still be classified by title).
    """
    total = len(articles)
    success = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_article = {
            executor.submit(scrape_article, article["url"]): article
            for article in articles
        }

        for i, future in enumerate(as_completed(future_to_article), 1):
            article = future_to_article[future]

            try:
                text, resolved_url = future.result()
            except Exception:
                logger.exception("Unexpected error scraping: %s", article["url"][:80])
                text, resolved_url = None, article["url"]

            article["full_text"] = text
            article["url"] = resolved_url

            if text:
                success += 1
            else:
                failed += 1

            if i % 50 == 0 or i == total:
                logger.info("Scraping progress: %d/%d done", i, total)

    logger.info("Scraping done: %d success, %d failed", success, failed)
    return articles
