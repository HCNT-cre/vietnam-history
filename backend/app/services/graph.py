from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from app.config import get_settings

settings = get_settings()


class GraphService:
    def __init__(self) -> None:
        self._driver = None
        self._init_error: Exception | None = None
        try:
            self._driver = GraphDatabase.driver(
                settings.graph_uri,
                auth=(settings.graph_user, settings.graph_password),
            )
        except Exception as exc:  # pragma: no cover - init guard
            self._init_error = exc

    def get_links_for_chunks(self, chunk_ids: list[int], limit: int = 4) -> list[dict]:
        if not chunk_ids or self._driver is None:
            return []
        query = """
        MATCH (c:Chunk)
        WHERE c.chunk_id IN $chunk_ids
        OPTIONAL MATCH (c)<-[:MENTIONED_IN]-(e:Entity)
        OPTIONAL MATCH (c)-[:BELONGS_TO]->(d:Dynasty)
        WITH c, d, collect(DISTINCT e.name) AS entities
        RETURN c.chunk_id AS chunk_id,
               coalesce(c.summary, substring(c.text,0,220)) AS summary,
               d.name AS dynasty,
               entities
        ORDER BY c.chunk_id
        LIMIT $limit
        """
        with self._driver.session(database=settings.graph_database) as session:
            records = session.run(query, chunk_ids=chunk_ids, limit=limit).data()
        links: list[dict[str, Any]] = []
        for record in records:
            dynasty = record.get("dynasty") or "Tư liệu"
            entities = record.get("entities") or []
            label = f"{dynasty} · {', '.join(entities[:3])}" if entities else dynasty
            links.append(
                {
                    "relation": label,
                    "description": record.get("summary") or "",
                    "chunk_id": int(record.get("chunk_id")) if record.get("chunk_id") is not None else None,
                }
            )
        return links


graph_service = GraphService()
