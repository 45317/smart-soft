import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.contrib import messages
from django.core.cache import cache

from .pipeline import chat, list_documents, upload_text_document, upload_pdf_document, delete_document

logger = logging.getLogger("django_rag")

RAG_DOCS_TTL = 300


def _rag_documents(user_id):
    try:
        result = list_documents(user_id)
        return result.get("documents", []) if isinstance(result, dict) else []
    except Exception as e:
        logger.error("RAG document list failed for %s: %s", user_id, e)
        return None


@login_required
@csrf_exempt
def rag_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            payload = {}
    except (ValueError, TypeError):
        payload = {}

    user_id = payload.get("user_id") or request.POST.get("user_id") or str(request.user.id)
    question = payload.get("question") or request.POST.get("question")
    top_k = payload.get("top_k") or request.POST.get("top_k") or 5

    if not question:
        return JsonResponse({"error": "question is required"}, status=400)

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 5

    try:
        result = chat(user_id, question, top_k)
    except Exception as e:
        logger.error("RAG chat failed: %s", e)
        result = {"error": str(e)}

    return JsonResponse(result)


@login_required
@csrf_exempt
def rag_upload(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    user_id = request.POST.get("user_id") or str(request.user.id)
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return JsonResponse({"error": "file field is required"}, status=400)

    filename = uploaded_file.name or "upload"

    try:
        if filename.lower().endswith(".pdf"):
            result = upload_pdf_document(user_id, uploaded_file.read(), filename)
        else:
            text = uploaded_file.read().decode("utf-8", errors="replace")
            result = upload_text_document(user_id, text, filename)
    except Exception as e:
        logger.error("RAG upload failed: %s", e)
        result = {"error": str(e)}

    return JsonResponse(result)


@login_required
@csrf_exempt
def rag_page(request):
    user_id = str(request.user.id)
    result = None
    question = ""
    top_k = 5
    cache_key = "rag_docs_{}".format(user_id)

    if request.method == "POST":
        if request.FILES.get("file"):
            uploaded = request.FILES["file"]
            filename = uploaded.name or "upload"
            try:
                if filename.lower().endswith(".pdf"):
                    result = upload_pdf_document(user_id, uploaded.read(), filename)
                else:
                    text = uploaded.read().decode("utf-8", errors="replace")
                    result = upload_text_document(user_id, text, filename)
                if result.get("success"):
                    messages.success(request, "Document uploaded successfully")
                    cache.delete(cache_key)
            except Exception as e:
                result = {"error": str(e)}
        elif request.POST.get("delete_document"):
            did = request.POST["delete_document"]
            result = delete_document(user_id, did)
            if result.get("success"):
                messages.success(request, "Document deleted")
                cache.delete(cache_key)
        elif request.POST.get("question"):
            question = request.POST["question"]
            try:
                top_k = int(request.POST.get("top_k") or 5)
            except (TypeError, ValueError):
                top_k = 5
            try:
                result = chat(user_id, question, top_k)
            except Exception as e:
                result = {"error": str(e)}

        if isinstance(result, dict) and result.get("error"):
            messages.error(request, result["error"])

    documents = cache.get_or_set(
        cache_key, lambda: _rag_documents(user_id), RAG_DOCS_TTL,
    )

    answer = result.get("answer") if isinstance(result, dict) and result.get("answer") else None
    sources = result.get("sources") if isinstance(result, dict) else None

    return render(request, "django_rag/rag.html", {
        "user_id": user_id,
        "documents": documents,
        "answer": answer,
        "sources": sources,
        "question": question,
        "top_k": top_k,
    })
