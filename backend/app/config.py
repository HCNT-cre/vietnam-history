from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VietSaga API"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./vietsaga.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "super-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expires: int = 3600  # seconds
    refresh_token_expires: int = 60 * 60 * 24 * 14

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-large"
    openai_embed_dimensions: int = 3072
    temperature: float = 0.3

    rag_top_k: int = 4
    rag_index_path: str = "./rag/faiss.index"
    rag_meta_path: str = "./rag/meta.json"
    rag_manifest_path: str = "./rag/rag_manifest.json"
    rag_pdf_path: str = "./rag/viet_nam_su_luoc.pdf"
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120

    milvus_host: str = "localhost"
    milvus_port: str = "19530"
    milvus_collection: str = "vnhistory_chunks"

    graph_uri: str = "neo4j://localhost:7687"
    graph_user: str = "neo4j"
    graph_password: str = "password"
    graph_database: str = "neo4j"

    allowed_origins: str = "http://localhost:5174"

    email_sender: str = "hello@vietsaga.app"
    email_api_key: str | None = None

    log_level: str = "info"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    def get_allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string thành list."""
        if isinstance(self.allowed_origins, str):
            return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return [self.allowed_origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()
