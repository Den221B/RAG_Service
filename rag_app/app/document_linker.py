import os
import re
import unicodedata
from typing import List

from config import settings

DOCUMENTS = [
    f for f in os.listdir(settings.documents_dir)
    if f.endswith(".pdf") and not f.startswith(("~", "."))
]

# Normalize file names and create mapping: {normalized_name: original_name}
DOC_MAP = {
    unicodedata.normalize("NFKD", os.path.splitext(f)[0].lower().replace("\xa0", " ").strip()): f
    for f in DOCUMENTS
}

# Pattern: "Document: <name>.pdf contains"
LINK_PATTERN = re.compile(
    r"Document (?P<name>[^:\n]+\.pdf) contains:",
    flags=re.IGNORECASE
)


def fast_link_injection(text: str, prefix_limit: int = 300) -> str:
    """
    Inserts a markdown link into the beginning of text if a document pattern is found.
    Only the first `prefix_limit` characters are processed.
    """
    prefix = text[:prefix_limit]
    suffix = text[prefix_limit:]

    def repl(m):
        raw = m.group("name").strip()
        normalized = unicodedata.normalize(
            "NFKD", os.path.splitext(raw)[0].lower().replace("\xa0", " ").strip()
        )
        matched = DOC_MAP.get(normalized)
        if matched:
            return (
                f"В документе: [{raw}](http://{settings.local_ip}:{settings.port}/files/{matched}) содержится информация"
            )
        return m.group(0)

    return LINK_PATTERN.sub(repl, prefix) + suffix


def inject_links_into_chunks(chunks: List[str], prefix_window: int = 300) -> List[str]:
    """
    Injects document links into each chunk (only scanning first `prefix_window` characters).
    """
    updated_chunks = []

    for text in chunks:
        prefix = text[:prefix_window]
        replaced = fast_link_injection(prefix)
        updated_chunks.append(replaced + text[prefix_window:])

    return updated_chunks
