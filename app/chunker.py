import re

def chunk_text(text: str, max_len: int = 600):
    """
    Делит текст на чанки по ~max_len символов, стараясь не резать предложения.
    """
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current = ""

    for sentence in sentences:
        # Если предложение длиннее лимита — режем его принудительно
        if len(sentence) > max_len:
            parts = [sentence[i:i+max_len] for i in range(0, len(sentence), max_len)]
            if current:
                chunks.append(current)
            chunks.extend(parts)
            current = ""
            continue

        # Нормальное поведение — собираем чанки
        if len(current) + len(sentence) + 1 <= max_len:
            current += " " + sentence if current else sentence
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks
