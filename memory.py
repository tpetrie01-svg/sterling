# memory.py
import json
import re
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent / "memory.json"

MAX_UNUSED_DAYS = 90  # non-critical memories unused this long get pruned

_LOCK = threading.Lock()

CAPTURE_RE = re.compile(
    r"(?:remember|don't forget|do not forget)\s+(?:that\s+)?(.+?)(?:[.!?]|$)",
    re.IGNORECASE,
)

# Facts matching this are treated as core identity info and are exempt from decay,
# regardless of how they were captured.
CRITICAL_RE = re.compile(
    r"\b(my name is|i'm called|call me|i live (?:in|at)|we live (?:in|at)|"
    r"i'm from|our (?:home|address|location)|my address|my birthday|"
    r"my wife|my husband|my partner|my son|my daughter|my kids|"
    r"i work at|my job is|i'm allergic to|my phone number|my email)\b",
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


def _load_full() -> list[dict]:
    if not MEMORY_FILE.is_file():
        return []
    return json.loads(MEMORY_FILE.read_text())


def _save(memories: list[dict]) -> None:
    MEMORY_FILE.write_text(json.dumps(memories, indent=2))


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS}


def _normalize(text: str) -> str:
    return " ".join(sorted(_tokens(text))) or text.strip().lower()


def _looks_critical(text: str) -> bool:
    return bool(CRITICAL_RE.search(text))


def _prune(memories: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_UNUSED_DAYS)
    kept = []
    for m in memories:
        if m.get("critical"):
            kept.append(m)
            continue
        last_used = datetime.fromisoformat(m.get("last_used", m["ts"]))
        if last_used >= cutoff:
            kept.append(m)
    return kept


def capture(prompt: str) -> str | None:
    """If prompt explicitly asks to remember something, return the extracted fact."""
    m = CAPTURE_RE.search(prompt)
    return m.group(1).strip() if m else None


def add(fact: str, critical: bool | None = None) -> None:
    """Add a fact, deduping against existing similar entries and pruning stale ones.

    critical=None auto-detects via keyword heuristic (name, location, etc.);
    pass True/False explicitly when the caller already knows (e.g. an LLM
    classification from implicit capture).
    """
    fact = fact.strip()
    if not fact:
        return
    if critical is None:
        critical = _looks_critical(fact)
    else:
        critical = critical or _looks_critical(fact)

    with _LOCK:
        memories = _load_full()
        now = datetime.now(timezone.utc).isoformat()
        norm = _normalize(fact)

        for m in memories:
            if _normalize(m["text"]) == norm:
                m["ts"] = now
                m["last_used"] = now
                m["critical"] = m.get("critical", False) or critical
                _save(memories)
                return

        memories.append({
            "text": fact,
            "ts": now,
            "last_used": now,
            "critical": critical,
        })
        _save(_prune(memories))


def relevant(prompt: str, max_results: int = 5) -> list[str]:
    """Return stored facts that share keywords with prompt, most-overlap first.
    Touches last_used on returned facts so they're protected from decay."""
    prompt_words = _tokens(prompt)
    if not prompt_words:
        return []

    with _LOCK:
        memories = _load_full()
        scored = []
        for m in memories:
            overlap = len(prompt_words & _tokens(m["text"]))
            if overlap:
                scored.append((overlap, m))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:max_results]

        if top:
            now = datetime.now(timezone.utc).isoformat()
            for _, m in top:
                m["last_used"] = now
            _save(memories)

        return [m["text"] for _, m in top]
