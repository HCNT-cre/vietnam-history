from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

from neo4j import GraphDatabase
from openai import OpenAI
from pypdf import PdfReader
from pymilvus import Collection, connections, utility

from app.config import get_settings
from app.services.rag import ensure_collection

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)

DYNASTY_KEYWORDS = {
    "HongBang": ["hồng bàng", "hùng vương", "lạc long quân", "âu cơ"],
    "BacThuoc": ["bắc thuộc", "triệu đà", "an dương vương", "tô định"],
    "Ly": ["lý", "thăng long", "lý công uẩn", "lý thái tổ"],
    "Tran": ["trần", "trần hưng đạo", "diên hồng", "bạch đằng"],
    "Le": ["lê", "lê lợi", "bình ngô", "nguyễn trãi"],
    "TaySon": ["tây sơn", "quang trung", "nguyễn huệ"],
    "Nguyen": ["nguyễn", "gia long", "tự đức", "đại nam"],
    "CanDai": ["cận đại", "kháng chiến", "hồ chí minh", "điện biên phủ"],
}

DYNASTY_LABELS = {
    "HongBang": "Thời Hồng Bàng",
    "BacThuoc": "Thời Bắc thuộc",
    "Ly": "Nhà Lý",
    "Tran": "Nhà Trần",
    "Le": "Nhà Lê",
    "TaySon": "Phong trào Tây Sơn",
    "Nguyen": "Nhà Nguyễn",
    "CanDai": "Cận đại",
    "Unknown": "Không rõ",
}

ENTITY_KEYWORDS = {
    "Lý Công Uẩn": ["lý công uẩn", "lý thái tổ"],
    "Trần Hưng Đạo": ["trần hưng đạo", "trần quốc tuấn"],
    "Lê Lợi": ["lê lợi"],
    "Nguyễn Trãi": ["nguyễn trãi"],
    "Nguyễn Huệ": ["nguyễn huệ", "quang trung"],
    "Gia Long": ["gia long", "nguyễn ánh"],
}


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    clean = " ".join(text.split())
    if len(clean) <= size:
        return [clean]
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = end - overlap
    return chunks


def detect_dynasty(text: str) -> str:
    lowered = text.lower()
    for dynasty, keywords in DYNASTY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return dynasty
    return "Unknown"


def detect_entities(text: str) -> list[str]:
    lowered = text.lower()
    entities: list[str] = []
    for name, keywords in ENTITY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            entities.append(name)
    return entities


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    payload = list(texts)
    embeddings: list[list[float]] = []
    for i in range(0, len(payload), 32):
        batch = payload[i : i + 32]
        resp = client.embeddings.create(model=settings.openai_embed_model, input=batch)
        for data in resp.data:
            embeddings.append(data.embedding)
    return embeddings


def build_vector_store(chunks: list[dict]) -> None:
    connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)
    if utility.has_collection(settings.milvus_collection):
        utility.drop_collection(settings.milvus_collection)
    ensure_collection(settings.milvus_collection, settings.openai_embed_dimensions)
    collection = Collection(settings.milvus_collection)
    collection.load()
    embeds = embed_texts([chunk["text"] for chunk in chunks])
    data = [
        [chunk["chunk_id"] for chunk in chunks],
        [chunk["text"] for chunk in chunks],
        [chunk["source"] for chunk in chunks],
        [chunk["period"] for chunk in chunks],
        [json.dumps(chunk["entities"], ensure_ascii=False) for chunk in chunks],
        embeds,
    ]
    collection.insert(data)
    collection.flush()


def rebuild_graph(chunks: list[dict]) -> None:
    driver = GraphDatabase.driver(
        settings.graph_uri, auth=(settings.graph_user, settings.graph_password)
    )
    with driver.session(database=settings.graph_database) as session:
        session.run("MATCH (c:Chunk) DETACH DELETE c")
        for chunk in chunks:
            session.run(
                """
                MERGE (d:Dynasty {slug:$period})
                  SET d.name = $dynasty
                MERGE (c:Chunk {chunk_id:$chunk_id})
                  SET c.text = $text,
                      c.summary = $summary,
                      c.source = $source
                MERGE (c)-[:BELONGS_TO]->(d)
                """,
                period=chunk["period"],
                dynasty=chunk["period_readable"],
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                summary=chunk["summary"],
                source=chunk["source"],
            )
            for entity in chunk["entities"]:
                session.run(
                    """
                    MERGE (e:Entity {name:$name})
                    WITH e
                    MATCH (c:Chunk {chunk_id:$chunk_id})
                    MERGE (e)-[:MENTIONED_IN]->(c)
                    """,
                    name=entity,
                    chunk_id=chunk["chunk_id"],
                )
        session.run("MATCH (e:Entity) WHERE NOT (e)-[:MENTIONED_IN]->() DETACH DELETE e")
    driver.close()


def main() -> None:
    pdf_path = Path(settings.rag_pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Không tìm thấy PDF tại {pdf_path}")
    text = extract_text(pdf_path)
    raw_chunks = chunk_text(
        text,
        size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
    )
    chunks: list[dict] = []
    for idx, chunk_text_value in enumerate(raw_chunks, start=1):
        period = detect_dynasty(chunk_text_value)
        entities = detect_entities(chunk_text_value)
        summary = chunk_text_value[:220] + ("…" if len(chunk_text_value) > 220 else "")
        chunks.append(
            {
                "chunk_id": idx,
                "text": chunk_text_value,
                "source": f"{pdf_path.name}",
                "period": period,
                "period_readable": DYNASTY_LABELS.get(period, "Không rõ"),
                "entities": entities,
                "summary": summary,
            }
        )

    build_vector_store(chunks)
    rebuild_graph(chunks)

    meta_path = Path(settings.rag_meta_path)
    meta_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ingested {len(chunks)} chunks into Milvus & Neo4j.")


if __name__ == "__main__":
    main()
