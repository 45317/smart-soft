import os
from django.conf import settings


def get_rag_data_dir():
    return getattr(settings, "RAG_DATA_DIR", os.path.join(settings.BASE_DIR, "rag_data"))


def get_embedding_model_name():
    return getattr(settings, "RAG_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")


def get_llm_model_name():
    return getattr(settings, "RAG_LLM_MODEL", "Qwen/Qwen2-0.5B-Instruct")


def get_timeout():
    return getattr(settings, "RAG_TIMEOUT", 60)


def get_max_context():
    return getattr(settings, "RAG_MAX_CONTEXT", 3000)


def get_top_k():
    return getattr(settings, "RAG_TOP_K", 5)
