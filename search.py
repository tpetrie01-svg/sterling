# search.py
import re
from ddgs import DDGS

TRIGGER_WORDS = (
    "today", "tonight", "yesterday", "this week", "this month", "this year",
    "latest", "current", "currently", "recent", "recently", "now",
    "news", "weather", "score", "price", "stock", "release date",
    "who is", "who won", "what happened",
)

YEAR_RE = re.compile(r"\b20\d{2}\b")


def needs_search(prompt: str) -> bool:
    p = prompt.lower()
    if any(w in p for w in TRIGGER_WORDS):
        return True
    return bool(YEAR_RE.search(p))


def web_search(query: str, max_results: int = 4) -> str:
    """Run a DuckDuckGo search and return formatted snippets, or "" on failure."""
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception:
        return ""
    if not results:
        return ""
    return "\n".join(f"- {r['title']}: {r['body']}" for r in results)
