import pytest

from app.core.config import settings
from app.services.embedding_service import get_embedding_service
from app.vectorstores.base import VectorStore
from app.vectorstores.chroma import ChromaVectorStore
from app.vectorstores.factory import get_vector_store


def test_factory_returns_chroma():
    get_vector_store.cache_clear()
    store = get_vector_store()
    assert isinstance(store, ChromaVectorStore)
    assert isinstance(store, VectorStore)
    get_vector_store.cache_clear()


def test_collection_name_matches_existing_convention():
    store = ChromaVectorStore()
    prefix = settings.vector_collection_prefix
    assert store.collection_name(global_docs=True) == f"{prefix}_global"
    assert store.collection_name() == f"{prefix}_default"
    assert store.collection_name(country_id=10) == f"{prefix}_country_10"


def test_embedding_service_is_singleton():
    get_embedding_service.cache_clear()
    assert get_embedding_service() is get_embedding_service()
    get_embedding_service.cache_clear()


def test_pinecone_is_not_enabled_yet(monkeypatch):
    monkeypatch.setattr("app.vectorstores.factory.settings.vector_db", "pinecone")
    get_vector_store.cache_clear()
    with pytest.raises(ValueError, match="not enabled"):
        get_vector_store()
    get_vector_store.cache_clear()
