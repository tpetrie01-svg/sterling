# ollama_client.py
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "sterling"  # match whatever `ollama list` shows

def get_response(prompt: str, search_context: str = "") -> str:
    full_prompt = prompt
    if search_context:
        full_prompt = (
            f"Web search results:\n{search_context}\n\n"
            f"Use them only if relevant, and don't mention the search itself. "
            f"User question: {prompt}"
        )

    r = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False
    })
    r.raise_for_status()
    return r.json()["response"]