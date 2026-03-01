"""Article summarization using Ollama (local LLM)."""

import logging

import requests

from config import SUMMARY_MAX_WORDS, SUMMARY_MIN_WORDS, SUMMARY_MODEL

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"


def summarize_text(text: str, title: str = "") -> str | None:
    """Generate a 30-40 word summary of the article text using Ollama."""
    if not text:
        return None

    # Truncate very long articles to fit in context window
    max_chars = 8_000
    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    prompt = (
        f"Summarize the following news article in exactly {SUMMARY_MIN_WORDS} to "
        f"{SUMMARY_MAX_WORDS} words. Write a single concise paragraph — no bullet "
        f"points, no preamble, just the summary.\n\n"
        f"Title: {title}\n\n"
        f"Article:\n{text}"
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": SUMMARY_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 100, "temperature": 0.3},
            },
            timeout=60,
        )
        resp.raise_for_status()
        summary = resp.json().get("response", "").strip()
        return summary if summary else None

    except requests.ConnectionError:
        logger.error("Cannot connect to Ollama — is it running? (ollama serve)")
        return None
    except Exception as exc:
        logger.warning("Ollama error for '%s': %s", title[:60], exc)
        return None


def summarize_articles(articles: list[dict]) -> list[dict]:
    """Add AI-generated summaries to each article."""
    success = 0
    failed = 0
    skipped = 0
    total = len(articles)

    for i, article in enumerate(articles):
        title = article.get("title", "")
        text = article.get("full_text")

        if not text:
            article["summary"] = None
            skipped += 1
            continue

        logger.info("Summarizing [%d/%d]: %s", i + 1, total, title[:60])

        summary = summarize_text(text, title)
        article["summary"] = summary

        if summary:
            success += 1
        else:
            failed += 1

    logger.info(
        "Summarization done: %d success, %d failed, %d skipped (no text)",
        success, failed, skipped,
    )
    return articles
