# ollama_client.py
from datetime import datetime
from pathlib import Path
import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_SHOW_URL = "http://localhost:11434/api/show"
MODEL_NAME = "sterling"  # match whatever `ollama list` shows

_MODELFILE_TEXT = (Path(__file__).parent / "Modelfile").read_text(encoding="utf-8")
PERSONA = re.search(r'SYSTEM """(.*?)"""', _MODELFILE_TEXT, re.DOTALL).group(1).strip()
# Ollama replaces the Modelfile's baked-in SYSTEM prompt with any system-role
# message present in the request, rather than adding to it. So every dynamic
# bit of context (persona included) has to be merged into a single system
# message per turn instead of appended as separate ones.

_context_length = None  # cached max context window for MODEL_NAME, lazily resolved


def get_context_length() -> int | None:
    """Best-effort lookup of the model's max context window, for displaying
    context usage as a fraction. Cached after the first successful call."""
    global _context_length
    if _context_length is not None:
        return _context_length
    try:
        r = requests.post(OLLAMA_SHOW_URL, json={"model": MODEL_NAME}, timeout=5)
        r.raise_for_status()
        model_info = r.json().get("model_info", {})
        for key, value in model_info.items():
            if key.endswith("context_length"):
                _context_length = int(value)
                break
    except Exception:
        pass
    return _context_length


def get_response(prompt: str, history: list, search_context: str = "", memories: list = None, search_error: str = None, weather_context: str = "", weather_error: str = None) -> tuple[str, int]:
    """history is a list of {"role": "user"|"assistant", "content": str} turns,
    oldest first. Mutated by the caller between calls, not by this function."""
    messages = list(history)
    now_str = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
    system_parts = [PERSONA, f"Current date and time: {now_str}."]
    if memories:
        facts = "\n".join(f"- {m}" for m in memories)
        system_parts.append(
            f"Long-term memory, things you've been told to remember about the user "
            f"in past sessions:\n{facts}\n\n"
            f"Use them only if relevant, and don't mention this note itself."
        )
    if search_context:
        system_parts.append(
            f"Web search results for the next question:\n{search_context}\n\n"
            f"Use them only if relevant, and don't mention the search itself."
        )
    elif search_error:
        system_parts.append(
            f"You tried to search the web for the next question but it failed: {search_error}. "
            f"Briefly tell the user you couldn't look this up right now, then answer from what you already know."
        )
    if weather_context:
        system_parts.append(
            f"Live weather data for the next question:\n{weather_context}\n\n"
            f"Use it only if relevant, and don't mention where the data came from."
        )
    elif weather_error:
        system_parts.append(
            f"You tried to look up the weather for the next question but it failed: {weather_error}."
        )
    messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    messages.append({"role": "user", "content": prompt})

    r = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    })
    r.raise_for_status()
    data = r.json()
    context_used = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
    return data["message"]["content"], context_used


_FACT_EXTRACT_SYSTEM = (
    "You extract durable personal facts about the user worth remembering across "
    "future sessions: identity, location, relationships, ongoing projects, "
    "recurring preferences or constraints. Ignore small talk, one-off questions, "
    "and anything not clearly stated by the user.\n"
    'Respond with ONLY a JSON object: {"facts": [{"text": "<fact as a standalone '
    'sentence>", "critical": true|false}]}. Mark critical=true only for core '
    "identity info (name, home location, relationships). If nothing is worth "
    'remembering, respond with {"facts": []}.'
)


def infer_facts(prompt: str, reply: str) -> list[dict]:
    """Ask the model whether this exchange contains a durable fact worth
    remembering, without the user having to say "remember...". Best-effort:
    returns [] on any parsing/network failure rather than raising."""
    messages = [
        {"role": "system", "content": _FACT_EXTRACT_SYSTEM},
        {"role": "user", "content": f"User said: {prompt}\nAssistant replied: {reply}"},
    ]
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "format": "json",
        }, timeout=15)
        r.raise_for_status()
        data = json.loads(r.json()["message"]["content"])
        facts = data.get("facts", [])
        return [
            {"text": f["text"].strip(), "critical": bool(f.get("critical"))}
            for f in facts
            if isinstance(f, dict) and f.get("text", "").strip()
        ]
    except Exception:
        return []