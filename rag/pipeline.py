import logging
from django.conf import settings

from .embeddings import encode_texts, encode_query, get_dimension
from .storage import get_user_store
from .documents import extract_pdf_text, create_chunks_with_metadata, generate_id
from .llm import generate_answer

logger = logging.getLogger(__name__)


def upload_text_document(user_id, text, filename):
    document_id = generate_id()
    store = get_user_store(user_id)
    dimension = get_dimension()
    store.init_index(dimension)

    chunk_size = getattr(settings, "RAG_CHUNK_SIZE", 500)
    chunk_overlap = getattr(settings, "RAG_CHUNK_OVERLAP", 100)

    chunks = create_chunks_with_metadata(text, document_id, user_id, filename, chunk_size, chunk_overlap)
    if not chunks:
        raise ValueError("Document produced no chunks")

    chunk_texts = [c["text"] for c in chunks]
    embeddings = encode_texts(chunk_texts)
    store.add_vectors(embeddings, chunks)
    store.save_document_raw(document_id, filename, text)
    store.metadata["documents"][document_id] = {"filename": filename, "chunks": len(chunks), "total_chars": len(text)}
    store._save_metadata()

    return {"success": True, "user_id": user_id, "document_id": document_id, "filename": filename, "chunks_added": len(chunks)}


def upload_pdf_document(user_id, file_content, filename):
    text = extract_pdf_text(file_content)
    document_id = generate_id()
    store = get_user_store(user_id)
    dimension = get_dimension()
    store.init_index(dimension)

    chunk_size = getattr(settings, "RAG_CHUNK_SIZE", 500)
    chunk_overlap = getattr(settings, "RAG_CHUNK_OVERLAP", 100)

    chunks = create_chunks_with_metadata(text, document_id, user_id, filename, chunk_size, chunk_overlap)
    if not chunks:
        raise ValueError("PDF produced no chunks")

    chunk_texts = [c["text"] for c in chunks]
    embeddings = encode_texts(chunk_texts)
    store.add_vectors(embeddings, chunks)
    store.save_document_raw(document_id, filename, text)
    store.metadata["documents"][document_id] = {"filename": filename, "chunks": len(chunks), "total_chars": len(text)}
    store._save_metadata()

    return {"success": True, "user_id": user_id, "document_id": document_id, "filename": filename, "chunks_added": len(chunks)}


def chat(user_id, question, top_k=None):
    if top_k is None:
        top_k = getattr(settings, "RAG_TOP_K", 5)
    max_context = getattr(settings, "RAG_MAX_CONTEXT_LENGTH", 2000)

    store = get_user_store(user_id)
    context = ""
    sources = []

    if store.faiss_index is not None and store.faiss_index.ntotal > 0:
        query_embedding = encode_query(question)
        results = store.search(query_embedding, top_k)
        if results:
            context_parts = []
            total_length = 0
            for result in results:
                text = result.get("text", "")
                if total_length + len(text) > max_context:
                    remaining = max_context - total_length
                    if remaining > 100:
                        text = text[:remaining]
                        context_parts.append(text)
                    break
                context_parts.append(text)
                total_length += len(text)
                sources.append({
                    "document_id": result.get("document_id", ""),
                    "filename": result.get("filename", ""),
                    "chunk_id": result.get("chunk_id", ""),
                    "score": round(result.get("score", 0.0), 4),
                })
            context = "\n\n".join(context_parts)

    answer = generate_answer(question, context)
    return {"user_id": user_id, "question": question, "answer": answer, "sources": sources}


def delete_document(user_id, document_id):
    store = get_user_store(user_id)
    if not store.document_exists(document_id):
        return {"success": False, "message": "Document not found", "document_id": document_id, "chunks_deleted": 0}
    chunks_deleted = store.delete_document(document_id)
    return {"success": True, "message": "Document deleted successfully", "document_id": document_id, "chunks_deleted": chunks_deleted}


def list_documents(user_id):
    store = get_user_store(user_id)
    return {"user_id": user_id, "documents": store.list_documents()}
