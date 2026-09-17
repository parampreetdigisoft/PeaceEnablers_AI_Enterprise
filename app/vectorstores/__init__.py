"""Vector-database adapters. Callers depend on VectorStore, never a specific backend."""

from app.vectorstores.base import VectorStore
from app.vectorstores.factory import get_vector_store

__all__ = ["VectorStore", "get_vector_store"]
