# voice.py
import subprocess
import wave
from pathlib import Path

# Resolve paths relative to this file's location, not the current working directory
BASE_DIR = Path(__file__).resolve().parent
VOICE_MODEL = BASE_DIR / "voices" / "en_GB-southern_english_female-low.onnx"
OUTPUT_WAV = BASE_DIR / "reply.wav"

def synthesize(text: str):
    subprocess.run(
        ["piper", "--model", str(VOICE_MODEL), "--output_file", str(OUTPUT_WAV)],
        input=text,
        text=True,
        check=True
    )

def get_wav_duration(path: str = None) -> float:
    wav_path = Path(path) if path else OUTPUT_WAV
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)