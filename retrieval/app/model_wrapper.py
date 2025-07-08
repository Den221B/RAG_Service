import pickle
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple, Optional

import faiss
import numpy as np
import torch
from FlagEmbedding import BGEM3FlagModel

from config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingBackend:
    """Wrapper around the embedding model and FAISS index."""

    def __init__(self) -> None:
        self.device = settings.device if torch.cuda.is_available() else "cpu"
        logger.info("Using device: %s", self.device)

        self.model = BGEM3FlagModel(
            model_name_or_path=settings.model_name,
            cache_dir=f"./models/{settings.model_name}",
            device=self.device,
            normalize_embeddings=True,
        )

        _ = self.model.encode(["warmup"], return_dense=True)

        self.faiss_index = self._load_faiss(Path(settings.faiss_index_path))
        self.metadata = self._load_metadata(Path(settings.metadata_path))

        logger.info("Loaded %d vectors into FAISS", self.faiss_index.ntotal)

    def encode(self, texts: List[str], *, mode: str = "dense", is_query: bool = False) -> np.ndarray:
        """
        Universal encoding method: dense or colbert.
        :param texts: List of texts to encode
        :param mode: 'dense' or 'colbert'
        :param is_query: Whether the input is a query
        :return: np.ndarray or list depending on mode
        """
        if not texts:
            raise ValueError("Input text list must not be empty.")

        if mode == "dense":
            if is_query:
                output = self.model.encode_queries(
                    texts,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False,
                )
            else:
                output = self.model.encode(
                    texts,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False
                )
            return np.asarray(output["dense_vecs"], dtype=np.float32)

        elif mode == "colbert":
            if is_query:
                output = self.model.encode_queries(
                    texts,
                    return_dense=False,
                    return_sparse=False,
                    return_colbert_vecs=True,
                )
            else:
                output = self.model.encode(
                    texts,
                    return_dense=False,
                    return_sparse=False,
                    return_colbert_vecs=True
                )
            return output["colbert_vecs"]

        else:
            raise ValueError("Unsupported encode mode: must be 'dense' or 'colbert'")

    def get_top_chunks(
        self,
        *,
        question: str,
        k: int,
        top_n: int,
        use_reranker: bool,
    ) -> Tuple[List[str], List[Optional[float]], float, float]:
        """
        Returns: (top chunks, their scores, faiss time, rerank time)
        """
        assert top_n <= k, "top_n cannot be greater than k"

        t0 = time.perf_counter()
        q_vec = self.encode([question], mode="dense", is_query=True)[0]
        _, idx = self.faiss_index.search(np.asarray([q_vec]), k)
        faiss_t = time.perf_counter() - t0

        candidates = [self.metadata[i] for i in idx[0]]

        rerank_t = 0.0
        if use_reranker and not settings.disable_colbert:
            try:
                t1 = time.perf_counter()
                chunks, scores = self._rerank(question, candidates, top_n)
                rerank_t = time.perf_counter() - t1
            except Exception:
                logger.exception("❌ ColBERT rerank failed. Returning top_n without rerank.")
                chunks = candidates[:top_n]
                scores = [None] * len(chunks)
        else:
            logger.warning("⚠️ ColBERT is disabled or not used — skipping rerank.")
            chunks = candidates[:top_n]
            scores = [None] * len(chunks)

        return chunks, scores, faiss_t, rerank_t

    def _rerank(self, question: str, chunks: List[str], top_n: int) -> Tuple[List[str], List[float]]:
        """ColBERT MaxSim rerank."""
        q_col = self.encode([question], mode="colbert", is_query=True)[0]
        p_cols = self.encode(chunks, mode="colbert", is_query=False)

        scored = []
        for chunk, p_vec in zip(chunks, p_cols):
            score = float(self.model.colbert_score(q_col, p_vec))
            scored.append((chunk, score))

        if not scored:
            return [], []

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_n]
        return [c for c, _ in top], [s for _, s in top]

    @staticmethod
    def _load_faiss(path: Path) -> faiss.Index:
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            return faiss.read_index(str(path))
        except Exception as e:
            logger.exception(f"Failed to load FAISS index: {e}")
            raise RuntimeError("Could not load FAISS index") from e

    @staticmethod
    def _load_metadata(path: Path) -> List[str]:
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.exception(f"Failed to load metadata: {e}")
            raise RuntimeError("Could not load metadata") from e


@lru_cache(maxsize=1)
def get_backend() -> EmbeddingBackend:
    try:
        return EmbeddingBackend()
    except Exception as e:
        logger.critical(f"EmbeddingBackend initialization failed: {e}")
        raise RuntimeError("Failed to initialize EmbeddingBackend") from e
