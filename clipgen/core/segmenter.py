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
