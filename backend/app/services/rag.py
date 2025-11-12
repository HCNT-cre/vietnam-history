from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config import get_settings

settings = get_settings()


@dataclass
class RetrievedChunk:
    chunk_id: int
    text: str
    source: str
    dynasty: str | None
    entities: list[str]
    score: float


class RAGService:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._collection: Collection | None = None
        self._init_error: Exception | None = None
        try:
            self._connect_vector_store()
            self._collection = self._load_collection()
        except Exception as exc:  # pragma: no cover - init guard
            self._init_error = exc

    def _connect_vector_store(self) -> None:
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )

    def _load_collection(self) -> Collection:
        if not utility.has_collection(settings.milvus_collection):
            return None
        collection = Collection(settings.milvus_collection)
        collection.load()
        return collection

    def _embed(self, text: str) -> list[float]:
        if not text:
            return [0.0] * settings.openai_embed_dimensions
        response = self._client.embeddings.create(
            model=settings.openai_embed_model,
            input=text,
        )
        return response.data[0].embedding

    def retrieve(self, query: str, top_k: int | None = None, filters: dict[str, Any] | None = None) -> list[dict]:
        if self._collection is None:
            raise RuntimeError(
                "Milvus collection chưa được khởi tạo. Hãy chạy script build_rag trước khi truy vấn."
            )
        if top_k is None:
            top_k = settings.rag_top_k
        embedding = self._embed(query)
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        expr = None
        if filters and filters.get("period"):
            periods = filters["period"]
            if isinstance(periods, (list, tuple)):
                period_list = ",".join([f'"{p}"' for p in periods])
                expr = f"period in [{period_list}]"
        results = self._collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["chunk_id", "text", "source", "period", "entities"],
            expr=expr,
        )
        if not results:
            return []
        chunks: list[dict] = []
        for hit in results[0]:
            entity = hit.entity
            chunk_id = entity.get("chunk_id")
            if chunk_id is None:
                chunk_id = hit.id
            metadata = entity.get("entities")
            entities = []
            if metadata:
                try:
                    entities = json.loads(metadata)
                except json.JSONDecodeError:
                    entities = [metadata]
            chunks.append(
                {
                    "chunk_id": int(chunk_id),
                    "text": entity.get("text") or "",
                    "source": entity.get("source") or "",
                    "dynasty": entity.get("period"),
                    "entities": entities,
                    "score": float(hit.score),
                }
            )
        return chunks

    def health(self) -> dict:
        if self._collection is None:
            return {
                "vector_collection": settings.milvus_collection,
                "documents": 0,
                "ready": False,
                "error": str(self._init_error) if self._init_error else "collection_not_initialized",
            }
        stats = self._collection.num_entities if hasattr(self._collection, "num_entities") else 0
        return {
            "vector_collection": settings.milvus_collection,
            "documents": stats,
            "ready": stats > 0,
        }


def ensure_collection(schema_name: str, dim: int) -> None:
    """Utility function used by the ingest script to bootstrap Milvus."""
    if utility.has_collection(schema_name):
        return
    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="period", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="entities", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    schema = CollectionSchema(fields=fields, description="Vietnam history knowledge chunks")
    collection = Collection(name=schema_name, schema=schema)
    index_params = {
        "metric_type": "IP",
        "index_type": "HNSW",
        "params": {"M": 16, "efConstruction": 200},
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    collection.load()


rag_service = RAGService()
