"""Entity classification — tag articles with matching companies."""

import logging
import re

from config import COMPANIES

logger = logging.getLogger(__name__)


def classify_article(article: dict) -> list[str]:
    """Return a list of company names that match the article.

    Matching is done against the title and (if available) the scraped text.
    A case-insensitive keyword search is used for speed and simplicity.
    """
    text = " ".join([
        article.get("title") or "",
        article.get("full_text") or "",
    ]).lower()

    matched: list[str] = []

    for company, keywords in COMPANIES.items():
        for kw in keywords:
            # Word-boundary match to avoid false positives
            pattern = r"(?:^|\W)" + re.escape(kw.lower()) + r"(?:\W|$)"
            if re.search(pattern, text):
                matched.append(company)
                break  # one keyword match is enough per company

    return matched


def classify_articles(articles: list[dict]) -> list[dict]:
    """Classify a batch of articles and attach company tags.

    Articles that don't match any company are excluded.
    """
    classified = []
    skipped = 0

    for article in articles:
        tags = classify_article(article)
        if tags:
            article["companies"] = tags
            classified.append(article)
        else:
            skipped += 1
            logger.debug("Skipped (no company match): %s", article.get("title", "")[:80])

    logger.info(
        "Classification: %d matched, %d skipped (no company match)",
        len(classified),
        skipped,
    )
    return classified
