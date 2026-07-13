# search.py
import logging
import re
from ddgs import DDGS
from ddgs.exceptions import RatelimitException, TimeoutException

logger = logging.getLogger(__name__)

TRIGGER_WORDS = (
    "today", "tonight", "yesterday", "tomorrow", "this week", "this month", "this year",
    "latest", "current", "currently", "recent", "recently", "now",
    "news", "score", "price", "stock", "release date",
    "who is", "who won", "what happened",
    # explicit search intent, regardless of whether the topic is time-sensitive
    "search", "look up", "look that up", "look it up", "google",
    "find out", "look online", "check online",
)

YEAR_RE = re.compile(r"\b20\d{2}\b")


def needs_search(prompt: str) -> bool:
    p = prompt.lower()
    if any(w in p for w in TRIGGER_WORDS):
        return True
    return bool(YEAR_RE.search(p))


def web_search(query: str, max_results: int = 4) -> tuple[str, str | None]:
    """Run a DuckDuckGo search.

    Returns (snippets, error). On success `error` is None and `snippets` holds
    the formatted results (possibly "" if there were none). On failure
    `snippets` is "" and `error` is a short human-readable reason the caller
    can pass on to the LLM so it can tell the user the search didn't happen.
    """
    try:
        results = DDGS().text(query, max_results=max_results)
    except RatelimitException:
        logger.warning("web_search rate-limited for query: %r", query)
        return "", "rate-limited by the search provider"
    except TimeoutException:
        logger.warning("web_search timed out for query: %r", query)
        return "", "the search timed out"
    except Exception:
        logger.exception("web_search failed unexpectedly for query: %r", query)
        return "", "an unexpected error occurred"
    if not results:
        logger.info("web_search returned no results for query: %r", query)
        return "", None
    return "\n".join(f"- {r['title']}: {r['body']}" for r in results), None
