from flask import Flask, request, jsonify, send_from_directory, send_file, abort, Response
from ollama_client import get_response
from voice import synthesize, get_wav_duration
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


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "empty prompt"}), 400

    reply = get_response(prompt)
    wav_path = synthesize(reply)
    duration = get_wav_duration(wav_path)

    token = uuid.uuid4().hex
    CLIPS[token] = wav_path

    return jsonify({"reply": reply, "duration": duration, "audio": f"/audio/{token}"})


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