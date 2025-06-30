# chunker.py
from textwrap import wrap

def chunk_text(text, chunk_size=512, overlap=64):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks
