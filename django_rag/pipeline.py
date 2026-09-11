import logging
from .storage import get_user_store
from .embeddings import encode_texts, encode_query
from .documents import generate_id, extract_pdf_text, create_chunks_with_metadata
from .llm import generate_answer
from .config import get_top_k, get_max_context

logger = logging.getLogger("django_rag")


def upload_text_document(user_id, text, filename):
    if not text or not text.strip():
        return {"error": "Empty document"}

    doc_id = generate_id()
    chunks = create_chunks_with_metadata(text, doc_id, user_id, filename)
    if not chunks:
        return {"error": "No content to index"}

    texts = [c["text"] for c in chunks]
    embeddings = encode_texts(texts)

    store = get_user_store(user_id)
    store.add(chunks, embeddings)

    return {
        "success": True,
        "user_id": user_id,
        "document_id": doc_id,
        "filename": filename,
        "chunks_added": len(chunks),
    }


def upload_pdf_document(user_id, file_content, filename):
    text = extract_pdf_text(file_content)
    if not text.strip():
        return {"error": "Could not extract text from PDF"}
    return upload_text_document(user_id, text, filename)


def chat(user_id, question, top_k=None):
    if top_k is None:
        top_k = get_top_k()

    store = get_user_store(user_id)
    docs = store.list_docs()

    if docs:
        query_emb = encode_query(question)
        results = store.search(query_emb, top_k=top_k)

        context_parts = []
        for r in results:
            context_parts.append(r.get("text", ""))
        context = "\n\n".join(context_parts)[:get_max_context()]

        sources = []
        for r in results:
            sources.append({
                "document_id": r.get("document_id", ""),
                "filename": r.get("filename", ""),
                "chunk_id": r.get("chunk_id", ""),
                "score": r.get("score", 0),
            })
    else:
        context = ""
        sources = []

    try:
        answer = generate_answer(question, context)
    except Exception as e:
        logger.error("LLM error: %s", e)
        answer = f"Error generating answer: {str(e)}"

    return {
        "user_id": user_id,
        "question": question,
        "answer": answer,
        "sources": sources,
    }


def delete_document(user_id, document_id):
    store = get_user_store(user_id)
    deleted = store.delete_doc(document_id)
    if deleted > 0:
        return {"success": True, "message": "Document deleted", "document_id": document_id, "chunks_deleted": deleted}
    return {"error": "Document not found"}


def list_documents(user_id):
    store = get_user_store(user_id)
    return {"user_id": user_id, "documents": store.list_docs()}
