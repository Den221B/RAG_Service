import os
from pathlib import Path


class Settings:
    """
    Application configuration loaded from environment variables,
    with defaults and resolved paths.
    """
    BASE_DIR = Path(__file__).resolve().parent

    faiss_index_path: Path = Path(
        os.getenv("FAISS_INDEX_PATH", BASE_DIR / "vdb" / "index.faiss")
    )
    metadata_path: Path = Path(
        os.getenv("METADATA_PATH", BASE_DIR / "vdb" / "metadata.pkl")
    )
    log_dir: Path = Path(
        os.getenv("LOG_DIR", BASE_DIR / "logs")
    )

    model_name: str = os.getenv("MODEL_NAME", "BAAI/bge-m3")
    device: str = os.getenv("DEVICE", "cuda")
    disable_colbert: bool = os.getenv("DISABLE_COLBERT", "false").lower() == "true"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    service_name: str = os.getenv("SERVICE_NAME", "Retrieval service")


settings = Settings()
