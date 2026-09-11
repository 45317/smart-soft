import json
import logging
from pathlib import Path

import faiss
import numpy as np

logger = logging.getLogger(__name__)


def _get_rag_data_dir():
    from django.conf import settings
    return Path(getattr(settings, "RAG_DATA_DIR", "rag_data"))


class UserStore:
    def __init__(self, user_id):
        self.user_id = user_id
        self.rag_data_dir = _get_rag_data_dir()
        self.user_dir = self.rag_data_dir / user_id
        self.docs_dir = self.user_dir / "documents"
        self.index_dir = self.user_dir / "index"
        self.meta_file = self.user_dir / "metadata.json"
        self.faiss_index_file = self.index_dir / "index.faiss"
        self.faiss_id_map_file = self.index_dir / "id_map.json"

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.metadata = self._load_metadata()
        self.faiss_index = None
        self.id_map = []
        self._load_faiss()

    def _load_metadata(self):
        if self.meta_file.exists():
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"documents": {}}

    def _save_metadata(self):
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def _load_faiss(self):
        if self.faiss_index_file.exists() and self.faiss_id_map_file.exists():
            try:
                self.faiss_index = faiss.read_index(str(self.faiss_index_file))
                with open(self.faiss_id_map_file, "r", encoding="utf-8") as f:
                    self.id_map = json.load(f)
                return
            except Exception:
                pass
        self.faiss_index = None
        self.id_map = []

    def _save_faiss(self):
        if self.faiss_index is not None:
            faiss.write_index(self.faiss_index, str(self.faiss_index_file))
            with open(self.faiss_id_map_file, "w", encoding="utf-8") as f:
                json.dump(self.id_map, f, ensure_ascii=False, indent=2)

    def init_index(self, dimension):
        if self.faiss_index is None:
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.id_map = []

    def add_vectors(self, embeddings, chunk_metas):
        if self.faiss_index is None:
            raise RuntimeError("FAISS index not initialized")
        self.faiss_index.add(embeddings)
        self.id_map.extend(chunk_metas)
        self._save_faiss()
        self._save_metadata()

    def search(self, query_embedding, top_k):
        if self.faiss_index is None or self.faiss_index.ntotal == 0:
            return []
        actual_k = min(top_k, self.faiss_index.ntotal)
        scores, indices = self.faiss_index.search(query_embedding, actual_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.id_map):
                continue
            meta = self.id_map[idx].copy()
            meta["score"] = float(score)
            results.append(meta)
        return results

    def delete_document(self, document_id):
        if self.faiss_index is None or self.faiss_index.ntotal == 0:
            return 0
        if document_id not in self.metadata.get("documents", {}):
            return 0
        original_count = self.faiss_index.ntotal
        keep_mask = np.array([m.get("document_id") != document_id for m in self.id_map])
        chunks_to_remove = int(np.sum(~keep_mask))
        if chunks_to_remove == 0:
            return 0
        embeddings_to_keep = self.faiss_index.reconstruct_n(0, original_count)
        embeddings_to_keep = embeddings_to_keep[keep_mask]
        self.id_map = [m for m, keep in zip(self.id_map, keep_mask) if keep]
        del self.metadata["documents"][document_id]
        dimension = embeddings_to_keep.shape[1] if embeddings_to_keep.shape[0] > 0 else 384
        self.faiss_index = faiss.IndexFlatIP(dimension)
        if embeddings_to_keep.shape[0] > 0:
            self.faiss_index.add(embeddings_to_keep)
        doc_file = self.docs_dir / f"{document_id}.json"
        if doc_file.exists():
            doc_file.unlink()
        self._save_faiss()
        self._save_metadata()
        return chunks_to_remove

    def list_documents(self):
        docs = []
        for doc_id, doc_info in self.metadata.get("documents", {}).items():
            docs.append({
                "document_id": doc_id,
                "filename": doc_info.get("filename", "unknown"),
                "chunks": doc_info.get("chunks", 0),
            })
        return docs

    def document_exists(self, document_id):
        return document_id in self.metadata.get("documents", {})

    def save_document_raw(self, document_id, filename, text):
        doc_file = self.docs_dir / f"{document_id}.json"
        with open(doc_file, "w", encoding="utf-8") as f:
            json.dump({"document_id": document_id, "filename": filename, "text": text}, f, ensure_ascii=False, indent=2)


def get_user_store(user_id):
    return UserStore(user_id)


def list_all_users():
    rag_data_dir = _get_rag_data_dir()
    if not rag_data_dir.exists():
        return []
    return [d.name for d in rag_data_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
