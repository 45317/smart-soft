from django.urls import path
from . import views

urlpatterns = [
    path("rag/", views.rag_page, name="rag"),
    path("rag/chat/", views.rag_chat, name="rag_chat"),
    path("rag/upload/", views.rag_upload, name="rag_upload"),
]
