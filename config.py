"""Configuration constants for the financial news aggregator."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Target companies and their keyword variants for matching
COMPANIES = {
    "OpenAI": [
        "openai", "open ai", "chatgpt", "chat gpt", "gpt-4", "gpt-5",
        "sam altman", "dall-e", "dalle", "sora",
    ],
    "Anthropic": [
        "anthropic", "claude", "claude ai",
    ],
    "Google DeepMind": [
        "google deepmind", "deepmind", "gemini ai", "google gemini",
        "demis hassabis",
    ],
    "Microsoft": [
        "microsoft", "msft", "satya nadella", "azure ai", "copilot",
        "bing ai", "github copilot",
    ],
    "Meta": [
        "meta ai", "meta platforms", "llama model", "llama ai",
        "mark zuckerberg", "facebook ai", "meta llama",
    ],
}

# RSS feed URLs for news collection
RSS_FEEDS = [
    # Google News RSS — company-specific queries
    "https://news.google.com/rss/search?q=OpenAI&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Anthropic+AI&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Google+DeepMind&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Microsoft+AI&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Meta+AI&hl=en-US&gl=US&ceid=US:en",
    # Yahoo Finance RSS
    "https://finance.yahoo.com/news/rssindex",
    # General AI news
    "https://news.google.com/rss/search?q=artificial+intelligence+company&hl=en-US&gl=US&ceid=US:en",
]

# NewsAPI search queries
NEWSAPI_QUERIES = [
    "OpenAI",
    "Anthropic AI",
    "Google DeepMind",
    "Microsoft AI",
    "Meta AI Llama",
]

# Scraping settings
REQUEST_TIMEOUT = 15  # seconds
MAX_RETRIES = 2

# Summarization settings
SUMMARY_MODEL = "llama3.2:3b"
SUMMARY_MIN_WORDS = 30
SUMMARY_MAX_WORDS = 40

# Storage
DB_PATH = "news_articles.db"
CSV_PATH = "news_articles.csv"

# Collection window
DAYS_BACK = 7
