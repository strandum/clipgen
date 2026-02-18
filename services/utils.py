import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def log(msg: str):
    print(f"[ClipGen] {msg}", flush=True)


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
