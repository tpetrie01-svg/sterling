from flask import Flask, request, jsonify, send_from_directory
from ollama_client import get_response
from voice import synthesize, get_wav_duration
import webbrowser
import threading
import os

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "empty prompt"}), 400

    reply = get_response(prompt)
    synthesize(reply)
    duration = get_wav_duration("reply.wav")

    return jsonify({
        "reply": reply,
        "duration": duration
    })

@app.route("/audio")
def audio():
    return send_from_directory(".", "reply.wav")

def open_browser():
    webbrowser.open("http://localhost:5000")

if __name__ == "__main__":
    # Only open the browser once, not on Flask's auto-reload
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1, open_browser).start()
    app.run(debug=True, port=5000)