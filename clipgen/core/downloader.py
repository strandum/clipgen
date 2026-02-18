import subprocess

from clipgen.config import WORK_DIR
from clipgen.services.status_service import update_status
from clipgen.services.utils import get_youtube_title, safe_name, unique_project_dir


def download_youtube(url: str):
    update_status("Laster ned video...", 10, True)

    title = safe_name(get_youtube_title(url))
    project_dir = unique_project_dir(title)

    video_path = WORK_DIR / "video.mp4"
    if video_path.exists():
        video_path.unlink()

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
