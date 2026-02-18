import json

from clipgen.config import STATUS_FILE


def update_status(message: str, progress: int, working: bool):
    STATUS_FILE.write_text(
        json.dumps({"message": message, "progress": int(progress), "working": bool(working)}),
        encoding="utf-8"
    )
