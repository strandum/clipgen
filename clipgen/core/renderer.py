import subprocess
import shutil
from pathlib import Path

from clipgen.config import VERT_H, VERT_W, WORK_DIR


def ffmpeg_render(
    video_path: Path,
    start: float,
    end: float,
    ass_file: Path,
    output_file: Path,
):
    duration = max(0.1, end - start)

    # ---- COPY ASS TO SAFE TEMP LOCATION ----
    temp_ass = WORK_DIR / "temp_subs.ass"

    if temp_ass.exists():
        temp_ass.unlink()

    shutil.copyfile(ass_file, temp_ass)

    vf = (
        f"scale={VERT_W}:{VERT_H}:force_original_aspect_ratio=decrease,"
        f"pad={VERT_W}:{VERT_H}:(ow-iw)/2:(oh-ih)/2:white,"
        f"ass={temp_ass.name}"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "24",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_file),
    ]

    res = subprocess.run(
        cmd,
        cwd=str(WORK_DIR),  # 👈 Important
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if res.returncode != 0:
        err = (res.stderr or "Unknown ffmpeg error")[-1200:]
        raise RuntimeError(f"ffmpeg failed:\n{err}")

    # Clean temp file
    if temp_ass.exists():
        temp_ass.unlink()
