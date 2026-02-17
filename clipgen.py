import os
import re
import json
import sys
import warnings
import subprocess
from pathlib import Path

# --- Quiet down noisy libs (HF / symlink warnings etc.) ---
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).parent
WORK_DIR = BASE_DIR / "work"
OUTPUT_DIR = BASE_DIR / "output"
STATUS_FILE = BASE_DIR / "status.json"

WORK_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

VERT_W = 720
VERT_H = 1280
SUB_MARGIN_V = 180


# ---------------- Logging ----------------

def log(msg: str):
    print(f"[ClipGen] {msg}", flush=True)


# ---------------- Status ----------------

def update_status(message: str, progress: int, working: bool):
    STATUS_FILE.write_text(
        json.dumps({"message": message, "progress": int(progress), "working": bool(working)}),
        encoding="utf-8"
    )


# ---------------- Utils ----------------

def safe_name(name: str, max_len: int = 80) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:\*\?\"<>\|]", "", name)       # remove invalid win chars
    name = re.sub(r"\s+", " ", name)
    name = name[:max_len].strip()
    return name or "Project"


def unique_project_dir(base_name: str) -> Path:
    d = OUTPUT_DIR / base_name
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        return d

    # Add suffix if exists
    n = 2
    while True:
        dd = OUTPUT_DIR / f"{base_name} ({n})"
        if not dd.exists():
            dd.mkdir(parents=True, exist_ok=True)
            return dd
        n += 1


# ---------------- YouTube download ----------------

def get_youtube_title(url: str) -> str:
    # Quiet call to yt-dlp to fetch title
    try:
        res = subprocess.run(
            ["yt-dlp", "--get-title", url],
            capture_output=True,
            text=True
        )
        title = (res.stdout or "").strip()
        if title:
            return title
    except Exception:
        pass
    return "Project"


def download_youtube(url: str):
    update_status("Laster ned video...", 10, True)

    title = safe_name(get_youtube_title(url))
    project_dir = unique_project_dir(title)

    video_path = WORK_DIR / "video.mp4"
    if video_path.exists():
        video_path.unlink()  # ensure new download

    # Quiet yt-dlp download (errors still captured)
    res = subprocess.run(
        ["yt-dlp", "-f", "mp4", "-o", str(video_path), url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
    )

    if res.returncode != 0 or not video_path.exists():
        err = (res.stderr or "Unknown yt-dlp error")[:500]
        raise RuntimeError(f"yt-dlp failed: {err}")

    return video_path, project_dir


# ---------------- Whisper ----------------

def load_whisper_model():
    # Use base for better quality; CPU int8 is ok
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


# ---------------- Text blocks ----------------

def words_to_sentences(words):
    sentences = []
    current = []
    start_time = None

    for w in words:
        if start_time is None:
            start_time = w["start"]

        current.append(w)

        if w["text"].endswith((".", "!", "?")):
            sentences.append({
                "start": start_time,
                "end": w["end"],
                "text": " ".join(x["text"] for x in current)
            })
            current = []
            start_time = None

    # flush tail
    if current:
        sentences.append({
            "start": start_time if start_time is not None else current[0]["start"],
            "end": current[-1]["end"],
            "text": " ".join(x["text"] for x in current)
        })

    return sentences


def build_blocks(sentences, block_size=3):
    blocks = []
    if len(sentences) < block_size:
        return blocks

    for i in range(len(sentences) - block_size + 1):
        chunk = sentences[i:i + block_size]
        blocks.append({
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
            "text": " ".join(s["text"] for s in chunk),
            "index": i
        })
    return blocks


# ---------------- ASS subtitles ----------------

def ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def generate_ass_for_range(words, start, end, ass_path: Path):
    lines = []

    for w in words:
        if w["start"] < start or w["end"] > end:
            continue

        s = w["start"] - start
        e = w["end"] - start
        word = w["text"].upper().strip()

        styled = r"{\fscx80\fscy80\t(0,120,\fscx110\fscy110)\t(120,220,\fscx100\fscy100)}" + word
        lines.append(f"Dialogue: 0,{ts(s)},{ts(e)},Default,,0,0,0,,{styled}")

    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VERT_W}
PlayResY: {VERT_H}

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,90,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,3,0,1,6,3,2,40,40,{SUB_MARGIN_V},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    content += "\n".join(lines)
    ass_path.write_text(content, encoding="utf-8")


# ---------------- FFmpeg render ----------------

def ffmpeg_render(video_path: Path, start: float, end: float, ass_file: Path, output_file: Path):
    duration = max(0.1, end - start)

    # Light themed canvas (white) + centered original + subtitles baked in
    vf = (
        f"scale={VERT_W}:{VERT_H}:force_original_aspect_ratio=decrease,"
        f"pad={VERT_W}:{VERT_H}:(ow-iw)/2:(oh-ih)/2:white,"
        f"ass={ass_file}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "24",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_file)
    ]

    # Quiet stdout, keep stderr for errors
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        err = (res.stderr or "Unknown ffmpeg error")[-900:]
        raise RuntimeError(f"ffmpeg failed: {err}")


# ---------------- MAIN ----------------

def main():
    update_status("Starter...", 3, True)

    url = input().strip()
    if not url:
        update_status("Ingen URL", 0, False)
        return

    clip_count = int(os.getenv("CLIP_COUNT", "3"))
    language = os.getenv("CLIP_LANGUAGE", "auto")

    try:
        log("Downloading...")
        video_path, project_dir = download_youtube(url)
        log(f"Project: {project_dir.name}")

        log("Transcribing...")
        words = transcribe_words(video_path, language=language)

        log("Building blocks...")
        sentences = words_to_sentences(words)
        blocks = build_blocks(sentences, 3)
        if not blocks:
            update_status("Fant ingen blokker.", 0, False)
            return

        # Simple spread: take blocks spaced out
        update_status("Velger klipp...", 45, True)
        min_distance = 45
        selected = []
        for b in blocks:
            if len(selected) >= clip_count:
                break
            if all(abs(b["start"] - s["start"]) >= min_distance for s in selected):
                selected.append(b)

        # fallback if not enough
        i = 0
        while len(selected) < clip_count and i < len(blocks):
            b = blocks[i]
            if all(abs(b["start"] - s["start"]) >= min_distance for s in selected):
                selected.append(b)
            i += 1

        update_status("Renderer klipp...", 60, True)

        for idx, b in enumerate(selected, start=1):
            start = max(0, b["start"] - 3)
            end = b["end"] + 3

            ass_file = project_dir / f"{idx:02d}.ass"
            out_file = project_dir / f"{idx:02d}_clip_vertical_subs.mp4"

            log(f"Rendering {idx}/{len(selected)}...")
            generate_ass_for_range(words, start, end, ass_file)
            ffmpeg_render(video_path, start, end, ass_file, out_file)

        update_status("Ferdig!", 100, False)
        log("Done.")

    except Exception as e:
        log(f"ERROR: {e}")
        update_status("Feil (se terminal)", 0, False)


if __name__ == "__main__":
    main()
