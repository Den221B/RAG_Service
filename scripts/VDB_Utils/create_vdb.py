import sys
from pathlib import Path
from typing import List

import numpy as np

from config import (
    DOCUMENTS_FOR_REBUILD,
    OUTPUT_FAISS_DIR,
    VOLUME_DOCUMENTS_DIR,
)
from extractor import extract_all_text
from file_utils import replace_documents
from ml_utils import (
    load_model,
    encode_chunks,
    create_index,
    save_index,
    save_metadata,
)


def create_vdb(
    documents_dir: Path,
    output_dir: Path,
    volume_documents: Path,
    use_tables: bool,
) -> None:
    """
    Create a FAISS vector database from a directory of documents.

    This function extracts text from documents, encodes them using a language model,
    creates a FAISS index from the embeddings, and saves the index and metadata.

    Args:
        documents_dir (Path): Directory containing the source documents.
        output_dir (Path): Directory where the FAISS index and metadata will be saved.
        volume_documents (Path): Destination for permanent document storage.
        use_tables (bool): Whether to include table descriptions via LLM.
    """
    if not documents_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {documents_dir}")

    print("Loading embedding model...")
    model = load_model()

    print("Extracting text from documents...")
    chunks: List[str] = extract_all_text(str(documents_dir), use_tables)
    print(f"Extracted {len(chunks)} chunks")

    print("Replacing documents in volume directory...")
    replace_documents(volume_documents, documents_dir)

    print("Encoding text chunks into embeddings...")
    embeddings = encode_chunks(model, chunks, max_length=2048)

    print("Creating FAISS index...")
    index = create_index(embeddings)

    print("Saving index and metadata...")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_index(index, output_dir / "index.faiss")
    save_metadata(chunks, output_dir / "metadata.pkl")

    print("✅ Vector database created successfully.")


if __name__ == "__main__":
    use_tables_flag = "--dont_use_tables" not in sys.argv
    create_vdb(
        documents_dir=DOCUMENTS_FOR_REBUILD,
        output_dir=OUTPUT_FAISS_DIR,
        volume_documents=VOLUME_DOCUMENTS_DIR,
        use_tables=use_tables_flag,
    )