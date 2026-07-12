# memory.py
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent / "memory.json"

CAPTURE_RE = re.compile(
    r"(?:remember|don't forget|do not forget)\s+(?:that\s+)?(.+?)(?:[.!?]|$)",
    re.IGNORECASE,
)

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his",
    "her", "its", "our", "their", "me", "him", "them", "us",
    "do", "does", "did", "what", "who", "where", "when", "why", "how",
    "to", "of", "in", "on", "at", "for", "and", "or", "but", "that",
    "this", "with", "about", "remember", "forget", "don't", "not",
}


def _load() -> list[str]:
    if not MEMORY_FILE.is_file():
        return []
    return [m["text"] for m in json.loads(MEMORY_FILE.read_text())]


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS}


def capture(prompt: str) -> str | None:
    """If prompt asks to remember something, return the extracted fact."""
    m = CAPTURE_RE.search(prompt)
    return m.group(1).strip() if m else None


def add(fact: str) -> None:
    memories = json.loads(MEMORY_FILE.read_text()) if MEMORY_FILE.is_file() else []
    memories.append({"text": fact, "ts": datetime.now(timezone.utc).isoformat()})
    MEMORY_FILE.write_text(json.dumps(memories, indent=2))


def relevant(prompt: str, max_results: int = 5) -> list[str]:
    """Return stored facts that share keywords with prompt, most-overlap first."""
    prompt_words = _tokens(prompt)
    if not prompt_words:
        return []

    scored = []
    for fact in _load():
        overlap = len(prompt_words & _tokens(fact))
        if overlap:
            scored.append((overlap, fact))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [fact for _, fact in scored[:max_results]]
