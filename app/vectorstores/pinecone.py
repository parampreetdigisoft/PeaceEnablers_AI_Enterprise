"""Pinecone vector store adapter — not enabled.

Install the commented `pinecone` package in requirements.txt, fill PINECONE_*
in .env, set VECTOR_DB=pinecone, uncomment this implementation, and uncomment
the factory branch in app/vectorstores/factory.py.
"""

# from __future__ import annotations
#
# import logging
# from typing import Any
#
# from app.core.config import settings
# from app.vectorstores.base import VectorStore
#
# logger = logging.getLogger(__name__)
#
#
# class PineconeVectorStore(VectorStore):
#     """Maps logical collection names to Pinecone namespaces in one index."""
#
#     def __init__(self) -> None:
#         self._index = None
#
#     def _client(self):
#         from pinecone import Pinecone
#
#         api_key = settings.pinecone_api_key
#         if not api_key:
#             raise ValueError("PINECONE_API_KEY is not set")
#         return Pinecone(api_key=api_key)
#
#     def _ensure(self) -> None:
#         if self._index is not None:
#             return
#         from pinecone import ServerlessSpec
#
#         pc = self._client()
#         name = settings.pinecone_index_name
#         if not pc.has_index(name):
#             pc.create_index(
#                 name=name,
#                 dimension=384,
#                 metric="cosine",
#                 spec=ServerlessSpec(
#                     cloud=settings.pinecone_cloud,
#                     region=settings.pinecone_region,
#                 ),
#             )
#         self._index = pc.Index(name)
#
#     def _filter(self, where: dict[str, Any] | None) -> dict[str, Any] | None:
#         if not where:
#             return None
#         out: dict[str, Any] = {}
#         for key, value in where.items():
#             if isinstance(value, dict):
#                 out[key] = value
#             else:
#                 out[key] = {"$eq": value}
#         return out
#
#     def query(
#         self,
#         name: str,
#         embedding: list[float],
#         n_results: int = 5,
#         where: dict[str, Any] | None = None,
#     ) -> list[str]:
#         try:
#             self._ensure()
#             kwargs: dict[str, Any] = {
#                 "vector": embedding,
#                 "top_k": n_results,
#                 "namespace": name,
#                 "include_metadata": True,
#             }
#             pinecone_filter = self._filter(where)
#             if pinecone_filter:
#                 kwargs["filter"] = pinecone_filter
#             result = self._index.query(**kwargs)
#             docs: list[str] = []
#             for match in result.get("matches") or []:
#                 meta = match.get("metadata") or {}
#                 text = meta.get("text") or meta.get("document")
#                 if text:
#                     docs.append(str(text))
#             return docs
#         except Exception as exc:
#             logger.warning("Vector query failed: %s", exc)
#             return []
#
#     def upsert(
#         self,
#         name: str,
#         ids: list[str],
#         documents: list[str],
#         embeddings: list[list[float]],
#         metadatas: list[dict] | None = None,
#     ) -> None:
#         self._ensure()
#         vectors = []
#         for i, vector_id in enumerate(ids):
#             meta = dict(metadatas[i]) if metadatas else {}
#             meta = {k: v for k, v in meta.items() if v is not None}
#             meta["text"] = documents[i]
#             vectors.append({"id": vector_id, "values": embeddings[i], "metadata": meta})
#         self._index.upsert(vectors=vectors, namespace=name)
#
#     def delete_where(self, name: str, where: dict[str, Any]) -> None:
#         try:
#             self._ensure()
#             pinecone_filter = self._filter(where)
#             if not pinecone_filter:
#                 return
#             self._index.delete(filter=pinecone_filter, namespace=name)
#         except Exception as exc:
#             logger.warning("Vector delete failed: %s", exc)
#
#     def healthy(self) -> bool:
#         try:
#             pc = self._client()
#             pc.describe_index(settings.pinecone_index_name)
#             return True
#         except Exception as exc:
#             logger.warning("Vector store unavailable: %s", exc)
#             return False
