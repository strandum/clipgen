import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATUS_FILE = BASE_DIR / "status.json"


def update_status(message: str, progress: int, working: bool):
    STATUS_FILE.write_text(
        json.dumps({"message": message, "progress": int(progress), "working": bool(working)}),
        encoding="utf-8"
    )
