from pathlib import Path
from typing import List

import pickle

import numpy as np
import torch
import faiss
from FlagEmbedding import BGEM3FlagModel

from config import MODEL_NAME, MODEL_PATH


def load_model() -> BGEM3FlagModel:
    """
    Load and initialize the BGEM3 model.

    Returns:
        BGEM3FlagModel: A loaded instance of the BGEM3 model.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return BGEM3FlagModel(
        MODEL_NAME,
        device=device,
        cache_dir=str(MODEL_PATH / MODEL_NAME),
        normalize_embeddings=True,
    )


def encode_chunks(
    model: BGEM3FlagModel,
    chunks: List[str],
    max_length: int = 8192,
    batch_size: int = 32,
) -> np.ndarray:
    """
    Encode a list of text chunks into dense embeddings.

    Args:
        model (BGEM3FlagModel): The embedding model.
        chunks (List[str]): List of text segments to encode.
        max_length (int, optional): Maximum token length. Defaults to 8192.
        batch_size (int, optional): Encoding batch size. Defaults to 32.

    Returns:
        np.ndarray: Dense embeddings of shape (N, D), dtype float32.
    """
    output = model.encode(
        chunks,
        batch_size=batch_size,
        max_length=max_length,
        return_dense=True,
    )
    return output["dense_vecs"].astype("float32")


def create_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Create a new FAISS index and populate it with embeddings.

    Args:
        embeddings (np.ndarray): Dense embeddings to index.

    Returns:
        faiss.Index: The initialized FAISS index.
    """
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def load_index(index_path: Path) -> faiss.Index:
    """
    Load a FAISS index from disk.

    Args:
        index_path (Path): Path to the saved FAISS index.

    Returns:
        faiss.Index: Loaded FAISS index.
    """
    return faiss.read_index(str(index_path))


def save_index(index: faiss.Index, index_path: Path) -> None:
    """
    Save a FAISS index to disk.

    Args:
        index (faiss.Index): FAISS index object.
        index_path (Path): Path where the index will be saved.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))


def load_metadata(metadata_path: Path) -> List[str]:
    """
    Load metadata (text chunks) from disk.

    Args:
        metadata_path (Path): Path to the metadata file.

    Returns:
        List[str]: List of text chunks.
    """
    if not metadata_path.exists():
        return []
    with open(metadata_path, "rb") as f:
        return pickle.load(f)


def save_metadata(metadata: List[str], metadata_path: Path) -> None:
    """
    Save metadata (text chunks) to disk.

    Args:
        metadata (List[str]): List of text chunks to save.
        metadata_path (Path): Path to the output file.
    """
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "wb") as f:
        pickle.dump(metadata, f)
