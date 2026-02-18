from pathlib import Path

from clipgen.services.status_service import update_status
from clipgen.services.utils import log
from faster_whisper import WhisperModel


def load_whisper_model():
    try:
        log("Using CUDA Whisper")
        return WhisperModel("base", device="cuda", compute_type="float16")
    except Exception:
        log("Using CPU Whisper")
        return WhisperModel("base", device="cpu", compute_type="int8")


def transcribe_words(video_path: Path, language="auto"):
    update_status("Transkriberer...", 25, True)
    model = load_whisper_model()

    kwargs = dict(word_timestamps=True)
    if language != "auto":
        kwargs["language"] = language

    segments, _ = model.transcribe(str(video_path), **kwargs)

    words = []
    for s in segments:
        for w in s.words:
            if not w.word:
                continue
            words.append({
                "start": float(w.start),
                "end": float(w.end),
                "text": w.word.strip()
            })

    return words
