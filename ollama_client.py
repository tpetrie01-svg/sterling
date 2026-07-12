# ollama_client.py
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "sterling"  # match whatever `ollama list` shows


def get_response(prompt: str, history: list, search_context: str = "", memories: list = None, search_error: str = None) -> str:
    """history is a list of {"role": "user"|"assistant", "content": str} turns,
    oldest first. Mutated by the caller between calls, not by this function."""
    messages = list(history)
    if memories:
        facts = "\n".join(f"- {m}" for m in memories)
        messages.append({
            "role": "system",
            "content": (
                f"Long-term memory, things you've been told to remember about the user "
                f"in past sessions:\n{facts}\n\n"
                f"Use them only if relevant, and don't mention this note itself."
            ),
        })
    if search_context:
        messages.append({
            "role": "system",
            "content": (
                f"Web search results for the next question:\n{search_context}\n\n"
                f"Use them only if relevant, and don't mention the search itself."
            ),
        })
    elif search_error:
        messages.append({
            "role": "system",
            "content": (
                f"You tried to search the web for the next question but it failed: {search_error}. "
                f"Briefly tell the user you couldn't look this up right now, then answer from what you already know."
            ),
        })
    messages.append({"role": "user", "content": prompt})

    r = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    })
    r.raise_for_status()
    return r.json()["message"]["content"]