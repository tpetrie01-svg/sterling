# ollama_client.py
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "sterling"  # match whatever `ollama list` shows

def get_response(prompt: str) -> str:
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    })
    r.raise_for_status()
    return r.json()["response"]