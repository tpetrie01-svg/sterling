# voice.py
import subprocess
import tempfile
import wave
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VOICE_MODEL = BASE_DIR / "voices" / "en_GB-southern_english_female-low.onnx"
EMOJI_RE = re.compile(
    "[" 
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


def synthesize(text: str) -> Path:
    text = EMOJI_RE.sub("", text).strip()
    """Synthesize text to a temp WAV outside the project dir. Returns its path."""
    fd, path = tempfile.mkstemp(prefix="sterling-", suffix=".wav")
    import os
    os.close(fd)  # piper writes the file itself
    out = Path(path)
    subprocess.run(
        ["piper", "--model", str(VOICE_MODEL), "--output_file", str(out)],
        input=text,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return out


def get_wav_duration(path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())