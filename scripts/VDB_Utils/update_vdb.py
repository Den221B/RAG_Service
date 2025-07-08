"""
Script to update an existing FAISS vector database with new documents.

This script removes duplicates, extracts new content, encodes it,
and appends it to the existing FAISS index and metadata.
"""

import sys
from pathlib import Path
from typing import List

import numpy as np
import faiss

from config import (
    DOCUMENTS_FOR_UPDATE,
    VOLUME_DOCUMENTS_DIR,
    OUTPUT_FAISS_DIR,
)
from extractor import extract_all_text
from file_utils import remove_duplicates, move_documents
from ml_utils import (
    load_model,
    encode_chunks,
    load_index,
    save_index,
    load_metadata,
    save_metadata,
)


def process_embeddings(new_chunks: List[str]) -> None:
    """
    Encode new text chunks and append them to the existing FAISS index and metadata.

    Args:
        new_chunks (List[str]): List of extracted text chunks.
    """
    if not new_chunks:
        print("No new chunks to index.")
        return

    print("Loading embedding model...")
    model = load_model()

    print(f"Encoding {len(new_chunks)} chunks...")
    embeddings = encode_chunks(model, new_chunks)

    index_path = OUTPUT_FAISS_DIR / "index.faiss"
    if index_path.exists():
        index = load_index(index_path)
    else:
        index = faiss.IndexFlatIP(embeddings.shape[1])

    index.add(embeddings)
    save_index(index, index_path)

    metadata_path = OUTPUT_FAISS_DIR / "metadata.pkl"
    metadata = load_metadata(metadata_path)
    metadata.extend(new_chunks)
    save_metadata(metadata, metadata_path)

    print("FAISS index and metadata updated successfully.")


def main(use_tables: bool) -> None:
    """
    Main update pipeline:
    - Remove duplicate documents
    - Extract text from new documents
    - Move new documents into permanent volume directory
    - Clean up update directory
    - Update FAISS index and metadata
    """
    print("Removing duplicate documents...")
    remove_duplicates(DOCUMENTS_FOR_UPDATE, VOLUME_DOCUMENTS_DIR)

    print("Extracting text from new documents...")
    new_chunks = extract_all_text(str(DOCUMENTS_FOR_UPDATE), use_tables)

    print("Moving new documents to volume directory...")
    move_documents(DOCUMENTS_FOR_UPDATE, VOLUME_DOCUMENTS_DIR)

    print(f"Cleaning directory: {DOCUMENTS_FOR_UPDATE}")
    for item in DOCUMENTS_FOR_UPDATE.iterdir():
        if item.is_file():
            item.unlink()

    process_embeddings(new_chunks)


if __name__ == "__main__":
    use_tables_flag = "--dont_use_tables" not in sys.argv
    main(use_tables_flag)
