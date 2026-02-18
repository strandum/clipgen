from pathlib import Path

from clipgen.config import SUB_MARGIN_V, VERT_H, VERT_W
from clipgen.services.utils import ts


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
