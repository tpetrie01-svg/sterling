from flask import Flask, request, jsonify, send_from_directory, send_file, abort, Response
from ollama_client import get_response, infer_facts, get_context_length
from voice import synthesize, get_wav_duration
from stt import transcribe
from search import needs_search, web_search
from weather import needs_weather, get_weather
import memory
from pathlib import Path
import tempfile
import webbrowser
import threading
import io
import os
import uuid

app = Flask(__name__, static_folder="static")

TMP_ROOT = Path(tempfile.gettempdir()).resolve()
CLIPS = {}  # token -> Path

HISTORY = []  # list of {"role": "user"|"assistant", "content": str}, oldest first
MAX_TURNS = 12  # keep the last N user+assistant pairs


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


def _remember_async(prompt: str, reply: str) -> None:
    """Runs off the request thread so implicit-memory inference never adds
    latency to the voice response."""
    for fact in infer_facts(prompt, reply):
        memory.add(fact["text"], critical=fact["critical"])


@app.route("/chat", methods=["POST"])
def chat():
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "empty prompt"}), 400

    fact = memory.capture(prompt)
    if fact:
        memory.add(fact)

    if needs_weather(prompt):
        weather_context, weather_error = get_weather(prompt)
        search_context, search_error = "", None
    else:
        weather_context, weather_error = "", None
        search_context, search_error = web_search(prompt) if needs_search(prompt) else ("", None)

    recalled = memory.relevant(prompt)
    reply, thinking, context_used = get_response(prompt, HISTORY, search_context, recalled, search_error, weather_context, weather_error)

    threading.Thread(target=_remember_async, args=(prompt, reply), daemon=True).start()

    HISTORY.append({"role": "user", "content": prompt})
    HISTORY.append({"role": "assistant", "content": reply})
    del HISTORY[:-MAX_TURNS * 2]

    wav_path = synthesize(reply)
    duration = get_wav_duration(wav_path)

    token = uuid.uuid4().hex
    CLIPS[token] = wav_path

    return jsonify({
        "reply": reply,
        "thinking": thinking,
        "duration": duration,
        "audio": f"/audio/{token}",
        "context_used": context_used,
        "context_max": get_context_length(),
    })


@app.route("/reset", methods=["POST"])
def reset():
    HISTORY.clear()
    return jsonify({"ok": True})


@app.route("/stt", methods=["POST"])
def stt():
    f = request.files.get("audio")
    if not f:
        return jsonify({"error": "no audio"}), 400
    fd, path = tempfile.mkstemp(prefix="stt-", suffix=".webm")
    os.close(fd)
    p = Path(path)
    f.save(p)
    try:
        return jsonify({"text": transcribe(p)})
    finally:
        p.unlink(missing_ok=True)


@app.route("/audio/<token>")
def audio(token):
    path = CLIPS.pop(token, None)  # one-shot: serve then forget
    if path is None or not path.is_file() or path.parent != TMP_ROOT:
        abort(404)
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return Response(data, mimetype="audio/wav")


def open_browser():
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1, open_browser).start()
    app.run(debug=True, port=5000)