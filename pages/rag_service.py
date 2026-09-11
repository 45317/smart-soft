"""Client for the local RAG API server running at http://localhost:8001.

Endpoints (all except /health require `Authorization: Bearer <key>`):
    GET     /health
    POST    /chat                                    JSON: user_id, question, top_k
    POST    /documents/text                          form: user_id, filename, text
    POST    /documents/pdf                           multipart: user_id + file
    GET     /documents/{user_id}
    DELETE  /documents/{user_id}/{document_id}

Every public method returns a ``dict``:

* a successful call returns the parsed JSON body of the response;
* a failed call (network error, timeout, or non-2xx status) returns
  ``{"error": "...", "status": <int|None>, "detail": <payload>}`` so callers
  can handle failures gracefully without raising.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_RAG_API_URL = "http://localhost:8001"
DEFAULT_RAG_API_KEY = "dev-key-change-me"
DEFAULT_RAG_TIMEOUT = 20


class RAGService:
    """Thin HTTP client around the RAG API."""

    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = (
            base_url or getattr(settings, "RAG_API_URL", DEFAULT_RAG_API_URL)
        ).rstrip("/")
        self.api_key = api_key or getattr(
            settings, "RAG_API_KEY", DEFAULT_RAG_API_KEY
        )
        self.timeout = timeout or int(getattr(settings, "RAG_TIMEOUT", DEFAULT_RAG_TIMEOUT))
        self.session = requests.Session()
        self.session.headers["Authorization"] = "Bearer {}".format(self.api_key)

    def health_check(self, timeout=None):
        """GET /health - the only endpoint that needs no auth header."""
        secs = timeout or self.timeout
        url = self.base_url + "/health"
        logger.debug("RAG health check at %s", url)
        try:
            resp = requests.get(url, timeout=secs)
        except requests.exceptions.Timeout:
            logger.error("RAG /health timed out after %ss", secs)
            return {"error": "health request timed out", "status": None}
        except requests.exceptions.RequestException as exc:
            logger.error("RAG /health request failed: %s", exc)
            return {"error": str(exc), "status": None}
        return self._decode(resp)

    def chat(self, user_id, question, top_k=5, timeout=None):
        """POST /chat with ``{"user_id", "question", "top_k"}``."""
        payload = {"user_id": user_id, "question": question, "top_k": top_k}
        logger.info("RAG chat for user %s (top_k=%s)", user_id, top_k)
        return self._request("POST", "/chat", timeout=timeout, json=payload)

    def upload_text(self, user_id, filename, text, timeout=None):
        """POST /documents/text with form fields ``user_id``, ``filename``, ``text``."""
        data = {"user_id": user_id, "filename": filename, "text": text}
        logger.info("RAG upload text '%s' for user %s", filename, user_id)
        return self._request("POST", "/documents/text", timeout=timeout, data=data)

    def upload_pdf(self, user_id, file, timeout=None):
        """POST /documents/pdf (multipart). ``file`` is a file-like object
        (e.g. an UploadedFile from ``request.FILES``) sent as the ``file``
        field; ``user_id`` is a form field."""
        files = {"file": file}
        data = {"user_id": user_id}
        logger.info("RAG upload pdf for user %s", user_id)
        return self._request("POST", "/documents/pdf", timeout=timeout, files=files, data=data)

    def list_documents(self, user_id, timeout=None):
        """GET /documents/{user_id}."""
        logger.info("RAG list documents for user %s", user_id)
        return self._request("GET", "/documents/{}".format(user_id), timeout=timeout)

    def delete_document(self, user_id, document_id, timeout=None):
        """DELETE /documents/{user_id}/{document_id}."""
        logger.info("RAG delete document %s for user %s", document_id, user_id)
        return self._request(
            "DELETE", "/documents/{}/{}".format(user_id, document_id),
            timeout=timeout,
        )

    # -- internal helpers -------------------------------------------- #
    def _request(self, method, path, timeout=None, **kwargs):
        secs = timeout or self.timeout
        url = self.base_url + path
        logger.debug("RAG %s %s", method, url)
        try:
            resp = self.session.request(method, url, timeout=secs, **kwargs)
        except requests.exceptions.Timeout:
            logger.error("RAG %s %s timed out after %ss", method, path, secs)
            return {"error": "request timed out", "status": None}
        except requests.exceptions.ConnectionError:
            logger.error("RAG %s %s: cannot reach %s", method, path, self.base_url)
            return {
                "error": "cannot reach RAG API at {}".format(self.base_url),
                "status": None,
            }
        except requests.exceptions.RequestException as exc:
            logger.error("RAG %s %s request failed: %s", method, path, exc)
            return {"error": str(exc), "status": None}
        return self._decode(resp)

    @staticmethod
    def _decode(resp):
        """Return parsed JSON for successful calls, error dict otherwise."""
        try:
            try:
                payload = resp.json()
            except ValueError:
                payload = resp.text
            if resp.status_code >= 400:
                logger.warning("RAG returned %s: %s", resp.status_code, payload)
                return {
                    "error": "RAG API returned {}".format(resp.status_code),
                    "status": resp.status_code,
                    "detail": payload,
                }
            return payload
        except Exception as exc:  # defensive: never crash a caller
            logger.error("RAG response decode failed: %s", exc)
            return {"error": "could not decode RAG response", "status": resp.status_code}


# Module-level singleton configured from Django settings.
rag_service = RAGService()