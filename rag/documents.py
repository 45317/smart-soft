import re
import uuid
import logging

logger = logging.getLogger(__name__)


def generate_id():
    return uuid.uuid4().hex[:12]


def extract_pdf_text(file_content):
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_content))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text and page_text.strip():
            text_parts.append(page_text.strip())
    if not text_parts:
        raise ValueError("PDF contains no extractable text")
    return "\n\n".join(text_parts)


def chunk_text(text, chunk_size=500, chunk_overlap=100):
    if not text or not text.strip():
        return []
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - chunk_overlap):
                    sub = para[i:i + chunk_size]
                    if sub.strip():
                        chunks.append(sub.strip())
                current_chunk = ""
            else:
                current_chunk = para
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def create_chunks_with_metadata(text, document_id, user_id, filename, chunk_size=500, chunk_overlap=100):
    raw_chunks = chunk_text(text, chunk_size, chunk_overlap)
    chunks_with_meta = []
    for i, chunk_text_content in enumerate(raw_chunks):
        chunk_id = f"{document_id}_chunk_{i:04d}"
        chunks_with_meta.append({
            "chunk_id": chunk_id,
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "chunk_index": i,
            "text": chunk_text_content,
        })
    return chunks_with_meta
