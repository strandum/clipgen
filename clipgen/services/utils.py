import re
import subprocess
from pathlib import Path

from clipgen.config import OUTPUT_DIR


def log(msg: str):
    print(f"[ClipGen] {msg}", flush=True)


def safe_name(name: str, max_len: int = 80) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:\*\?\"<>\|]", "", name)
    name = re.sub(r"\s+", " ", name)
    name = name[:max_len].strip()
    return name or "Project"


def unique_project_dir(base_name: str) -> Path:
    d = OUTPUT_DIR / base_name
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        return d

    n = 2
    while True:
        dd = OUTPUT_DIR / f"{base_name} ({n})"
        if not dd.exists():
            dd.mkdir(parents=True, exist_ok=True)
            return dd
        n += 1


def get_youtube_title(url: str) -> str:
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


def ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"
