import logging
import numpy as np

logger = logging.getLogger("django_rag")

_embedding_model = None
_model_dimension = 0


def get_embedding_model():
    global _embedding_model, _model_dimension
    if _embedding_model is None:
        from .config import get_embedding_model_name
        from sentence_transformers import SentenceTransformer

        model_name = get_embedding_model_name()
        logger.info("Loading embedding model: %s", model_name)
        _embedding_model = SentenceTransformer(model_name)
        _model_dimension = _embedding_model.get_embedding_dimension()
        logger.info("Embedding model loaded (dimension=%d)", _model_dimension)
    return _embedding_model


def get_dimension():
    global _model_dimension
    if _model_dimension == 0:
        get_embedding_model()
    return _model_dimension


def encode_texts(texts, batch_size=32):
    model = get_embedding_model()
    prefixed = []
    for text in texts:
        if not text.startswith("query: ") and not text.startswith("passage: "):
            prefixed.append(f"passage: {text}")
        else:
            prefixed.append(text)
    embeddings = model.encode(
        prefixed,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def encode_query(query):
    model = get_embedding_model()
    if not query.startswith("query: ") and not query.startswith("passage: "):
        q = f"query: {query}"
    else:
        q = query
    embedding = model.encode(
        [q],
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embedding.astype(np.float32)
