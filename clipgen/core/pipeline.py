import os

from clipgen.core.downloader import download_youtube
from clipgen.core.renderer import ffmpeg_render
from clipgen.core.segmenter import build_blocks, words_to_sentences
from clipgen.core.subtitles import generate_ass_for_range
from clipgen.core.transcriber import transcribe_words
from clipgen.services.status_service import update_status
from clipgen.services.utils import log


def run_pipeline():
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

        update_status("Velger klipp...", 45, True)
        min_distance = 45
        selected = []
        for b in blocks:
            if len(selected) >= clip_count:
                break
            if all(abs(b["start"] - s["start"]) >= min_distance for s in selected):
                selected.append(b)

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
    run_pipeline()
