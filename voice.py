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


def strip_markdown(text: str) -> str:
    """Strip Markdown syntax so TTS speaks plain words, not literal symbols."""
    text = re.sub(r"```(?:\w+\n)?([\s\S]*?)```", r"\1", text)          # fenced code blocks
    text = re.sub(r"`([^`]+)`", r"\1", text)                           # inline code
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)              # images
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)               # links
    text = re.sub(r"(\*\*\*|\*\*|\*|___|__|_)", "", text)              # bold/italic markers
    text = re.sub(r"~~(.*?)~~", r"\1", text)                           # strikethrough
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)  # headers
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)       # blockquotes
    text = re.sub(r"^\s{0,3}([-*_])\s*(\1\s*){2,}$", "", text, flags=re.MULTILINE)  # hr
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)       # unordered list markers
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)       # ordered list markers
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def synthesize(text: str) -> Path:
    """Synthesize text to a temp WAV outside the project dir. Returns its path."""
    text = strip_markdown(text)
    text = EMOJI_RE.sub("", text).strip()
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