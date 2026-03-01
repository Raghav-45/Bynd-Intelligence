"""Main entry point — orchestrates the full news aggregation pipeline."""

import logging
import sys
import time

from classifier import classify_articles
from collector import collect_all
from scraper import scrape_articles
from storage import export_csv, get_company_counts, init_db, store_articles
from summarizer import summarize_articles

# ── Logging setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", mode="w"),
    ],
)
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """Execute the full news aggregation pipeline."""
    start = time.time()

    # Step 1 — Collect articles from all sources
    logger.info("=" * 60)
    logger.info("STEP 1: Collecting articles from RSS feeds and NewsAPI")
    logger.info("=" * 60)
    raw_articles = collect_all()

    if not raw_articles:
        logger.error("No articles collected. Check your feeds/API keys.")
        return

    # Step 2 — Initial classification by title (pre-scrape filter)
    logger.info("=" * 60)
    logger.info("STEP 2: Initial classification (by title)")
    logger.info("=" * 60)
    pre_classified = classify_articles(raw_articles)

    if not pre_classified:
        logger.error("No articles matched any target company after initial classification.")
        return

    # Step 3 — Scrape full article text
    logger.info("=" * 60)
    logger.info("STEP 3: Scraping article content")
    logger.info("=" * 60)
    scraped = scrape_articles(pre_classified)

    # Step 4 — Re-classify with full text (may pick up additional company tags)
    logger.info("=" * 60)
    logger.info("STEP 4: Re-classifying with full text")
    logger.info("=" * 60)
    classified = classify_articles(scraped)

    # Step 5 — Generate AI summaries
    logger.info("=" * 60)
    logger.info("STEP 5: Generating AI summaries via Claude")
    logger.info("=" * 60)
    summarized = summarize_articles(classified)

    # Step 6 — Store in SQLite and export CSV
    logger.info("=" * 60)
    logger.info("STEP 6: Storing results")
    logger.info("=" * 60)
    conn = init_db()
    store_articles(summarized, conn)
    csv_path = export_csv(conn)

    # ── Final summary ────────────────────────────────────────────────────────
    elapsed = time.time() - start
    counts = get_company_counts(conn)
    conn.close()

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info("Time elapsed: %.1f seconds", elapsed)
    logger.info("Total unique articles stored: %d", sum(counts.values()))
    logger.info("CSV exported to: %s", csv_path)
    logger.info("")
    logger.info("Articles per company:")
    for company, count in sorted(counts.items(), key=lambda x: -x[1]):
        logger.info("  %-20s %d", company, count)
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
