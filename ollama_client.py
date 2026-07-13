# ollama_client.py
from datetime import datetime
from pathlib import Path
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "sterling"  # match whatever `ollama list` shows

_MODELFILE_TEXT = (Path(__file__).parent / "Modelfile").read_text(encoding="utf-8")
PERSONA = re.search(r'SYSTEM """(.*?)"""', _MODELFILE_TEXT, re.DOTALL).group(1).strip()
# Ollama replaces the Modelfile's baked-in SYSTEM prompt with any system-role
# message present in the request, rather than adding to it. So every dynamic
# bit of context (persona included) has to be merged into a single system
# message per turn instead of appended as separate ones.


def get_response(prompt: str, history: list, search_context: str = "", memories: list = None, search_error: str = None) -> str:
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
    messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    messages.append({"role": "user", "content": prompt})

    r = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    })
    r.raise_for_status()
    return r.json()["message"]["content"]