import os
import hashlib
import time
from pypdf import PdfReader


def generate_id():
    return hashlib.md5(f"{time.time()}{os.getpid()}".encode()).hexdigest()[:12]


def extract_pdf_text(file_content):
    import io

    reader = PdfReader(io.BytesIO(file_content))
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text


def chunk_text(text, chunk_size=500, chunk_overlap=100):
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - chunk_overlap
    return chunks


def create_chunks_with_metadata(text, document_id, user_id, filename, chunk_size=500, chunk_overlap=100):
    text_chunks = chunk_text(text, chunk_size, chunk_overlap)
    result = []
    for i, chunk in enumerate(text_chunks):
        result.append({
            "text": chunk,
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "chunk_id": f"{document_id}_chunk_{i:04d}",
        })
    return result
