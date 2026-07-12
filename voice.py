# voice.py
import subprocess
import wave

VOICE_MODEL = r"C:\piper\voices\en_GB-southern_english_female-low.onnx"
OUTPUT_WAV = "reply.wav"

def synthesize(text: str):
    subprocess.run(
        ["piper", "--model", VOICE_MODEL, "--output_file", OUTPUT_WAV],
        input=text,
        text=True,
        check=True
    )

def get_wav_duration(path: str = OUTPUT_WAV) -> float:
    with wave.open(path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)