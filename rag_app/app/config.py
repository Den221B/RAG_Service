import os
import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base paths -----------------------------------------------------
    base_dir: Path = Path(__file__).resolve().parent

    documents_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("documents_dir", Path(__file__).resolve().parent / "documents")
        )
    )

    log_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("log_dir", Path(__file__).resolve().parent / "logs")
        )
    )

    # Network --------------------------------------------------------
    port: int = 8001
    local_ip: str = "local_ip"

    # Service URLs ---------------------------------------------------
    retriever_url: str = "http://retrieval:8004/get_chunks"
    llm_url: str = "http://llm_server/v1/chat/completions"
    log_collector_url: str = "http://log_collector:8003/collect"

    # LLM ------------------------------------------------------------
    model_name: str = "qwen2.5-14b-instruct"
    temperature: float = 0.3
    max_generated_tokens: int = 1536

    # RAG ------------------------------------------------------------
    default_k: int = 50
    default_top_n: int = 5
    use_reranker: bool = True

    # Miscellaneous --------------------------------------------------
    api_key: str = "api_key"
    debug: bool = False
    timeout_clients: int = 100

    # System prompt --------------------------------------------------
    system_prompt: str = Field(
        default_factory=lambda: (
            Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"
        ).read_text(encoding="utf-8")
    )
    system_hints: List[Dict[str, Any]] = Field(
        default_factory=lambda: json.loads(
            (Path(__file__).resolve().parent / "prompts" / "system_hints.json").read_text(encoding="utf-8")
        )
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return singleton settings object."""
    return Settings()


settings: Settings = get_settings()
