import os
import json
import logging
import faiss
import numpy as np
from .config import get_rag_data_dir
from .embeddings import encode_texts, encode_query, get_dimension

logger = logging.getLogger("django_rag")


def _get_rag_data_dir():
    data_dir = get_rag_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class UserStore:
    def __init__(self, user_id):
        self.user_id = user_id
        self.user_dir = os.path.join(_get_rag_data_dir(), str(user_id))
        os.makedirs(self.user_dir, exist_ok=True)
        self.index_path = os.path.join(self.user_dir, "index.faiss")
        self.chunks_path = os.path.join(self.user_dir, "chunks.json")
        self._index = None
        self._chunks = []

    def _load(self):
        if self._index is not None:
            return
        if os.path.exists(self.chunks_path):
            with open(self.chunks_path, "r", encoding="utf-8") as f:
                self._chunks = json.load(f)
        if os.path.exists(self.index_path):
            self._index = faiss.read_index(self.index_path)
        else:
            dim = get_dimension()
            self._index = faiss.IndexFlatIP(dim)

    def _save(self):
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False, indent=2)
        faiss.write_index(self._index, self.index_path)

    def add(self, chunks, embeddings):
        self._load()
        self._index.add(embeddings)
        self._chunks.extend(chunks)
        self._save()

    def search(self, query_embedding, top_k=5):
        self._load()
        if len(self._chunks) == 0:
            return []
        k = min(top_k, len(self._chunks))
        scores, indices = self._index.search(query_embedding, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            chunk = self._chunks[idx].copy()
            chunk["score"] = float(score)
            results.append(chunk)
        return results

    def list_docs(self):
        self._load()
        docs = {}
        for chunk in self._chunks:
            doc_id = chunk.get("document_id", "unknown")
            if doc_id not in docs:
                docs[doc_id] = {"document_id": doc_id, "filename": chunk.get("filename", ""), "chunks": 0}
            docs[doc_id]["chunks"] += 1
        return list(docs.values())

    def delete_doc(self, document_id):
        self._load()
        old_count = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.get("document_id") != document_id]
        deleted = old_count - len(self._chunks)
        if deleted == 0:
            return 0

        if len(self._chunks) == 0:
            self._index = faiss.IndexFlatIP(get_dimension())
        else:
            remaining_texts = [c.get("text", "") for c in self._chunks]
            embeddings = encode_texts(remaining_texts)
            self._index = faiss.IndexFlatIP(get_dimension())
            self._index.add(embeddings)

        self._save()
        return deleted

    def get_user_id(self):
        return self.user_id


def get_user_store(user_id):
    return UserStore(user_id)


def list_all_users():
    data_dir = _get_rag_data_dir()
    if not os.path.exists(data_dir):
        return []
    return [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
