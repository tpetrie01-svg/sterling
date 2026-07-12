from faster_whisper import WhisperModel

_model = WhisperModel("base.en", device="cpu", compute_type="int8")

def transcribe(path) -> str:
    segments, _ = _model.transcribe(str(path))
    return " ".join(s.text for s in segments).strip()