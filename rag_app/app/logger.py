import logging
import os

from config import settings


def setup_logger() -> None:
    """
    Configure unified logging: console + file.
    Avoids reconfiguration if already set (e.g., on hot reload).
    """
    os.makedirs(settings.log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(settings.log_dir, "rag.log"), encoding="utf-8"),
            logging.StreamHandler()
        ]
    )