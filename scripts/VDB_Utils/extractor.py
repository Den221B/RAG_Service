import os
import re
import requests
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import camelot
from tqdm import tqdm
from docx import Document
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar

from config import LLM_URL, API_KEY


def _clean_table(text: str, trim_spaces: bool = True) -> str:
    """Clean and normalize table text."""
    if trim_spaces:
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"-{2,}", "-", text)
    return text.strip()


def _extract_tables(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables from a PDF file using Camelot.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        List[Dict[str, Any]]: Extracted table data with coordinates and content.
    """
    try:
        tables = camelot.read_pdf(pdf_path, pages="all")
    except Exception as e:
        print(f"Error extracting tables from {pdf_path}: {e}")
        return []

    results = []
    for table in tables:
        coords = table._bbox
        results.append({
            "content": f":{_clean_table(table.df.to_markdown(index=False))}\n",
            "coordinates": {"x0": coords[0], "y0": coords[1], "x1": coords[2], "y1": coords[3]},
            "page": table.page,
        })

    return results


def _element_intersects_table(el: Any, tbl: Dict[str, Any]) -> bool:
    """Check whether a PDF element overlaps with a table's bounding box."""
    ex0, ey0, ex1, ey1 = el.x0, el.y0, el.x1, el.y1
    tx0, ty0, tx1, ty1 = tbl["coordinates"].values()
    return not (ex1 < tx0 or ex0 > tx1 or ey1 < ty0 or ey0 > ty1)


def _describe_table_llm(table_markdown: str) -> Optional[str]:
    """
    Get a detailed table summary from an LLM.

    Args:
        table_markdown (str): The table content in markdown format.

    Returns:
        Optional[str]: LLM-generated table summary or None if failed.
    """
    if not LLM_URL:
        return None

    system_prompt = (
        "You are an expert at analyzing tables. "
        "Provide a detailed description of the table content without omitting anything. "
        "If the table lacks a title, generate one based on its content. "
        "List all mentioned entities, dates, amounts, and explain each part thoroughly."
    )

    payload = {
        "model": "qwen2.5-32b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": table_markdown},
        ],
        "temperature": 0.3,
        "n_predict": 2048,
        "stop": ["<|im_end|>"],
    }

    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

    try:
        response = requests.post(LLM_URL, json=payload, headers=headers, timeout=1000)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error from LLM: {e}")
        return None


def _extract_line(element: Any) -> Tuple[str, List[Tuple[str, float]]]:
    """
    Extract raw text and font info from a PDF element.

    Args:
        element (Any): PDFMiner layout element.

    Returns:
        Tuple[str, List[Tuple[str, float]]]: Raw line text and font characteristics.
    """
    text = element.get_text()
    formats = []
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            for char in text_line:
                if isinstance(char, LTChar):
                    formats.append((char.fontname, char.size))
    return text, list(set(formats))


def extract_text_and_tables(pdf_path: str, use_tables: bool = False) -> List[str]:
    """
    Extract paragraph-like chunks and optional table summaries from a PDF.

    Args:
        pdf_path (str): Path to the PDF file.
        use_tables (bool): Whether to include LLM summaries of tables.

    Returns:
        List[str]: Text chunks extracted from the document.
    """
    chunks: List[str] = []
    tables = _extract_tables(pdf_path)
    raw_lines: List[str] = []

    for pagenum, page in enumerate(extract_pages(pdf_path)):
        page_elements = sorted(((el.y1, el) for el in page._objs), key=lambda a: a[0], reverse=True)

        for _, el in page_elements:
            if not isinstance(el, LTTextContainer):
                continue

            intersects = any(
                pagenum == tbl["page"] - 1 and _element_intersects_table(el, tbl)
                for tbl in tables
            )
            if intersects:
                continue

            line_text, _ = _extract_line(el)
            raw_lines.append(line_text)

    full_text = "".join(raw_lines)
    full_text = re.sub(r"([^\w\s_])\1+", r"\1", full_text)
    full_text = re.sub(r"(?<![.:;])\n", " ", full_text)
    full_text = re.sub(r"_+", "", full_text)
    full_text = re.sub(r"(«\s*»|“\s*”)", "", full_text)
    full_text = re.sub(r" {2,}", " ", full_text).strip()

    buffer = ""
    for char in full_text:
        buffer += char
        if char == "\n" and len(buffer) >= 1000:
            chunks.append(buffer.strip())
            buffer = ""
    if buffer:
        chunks.append(buffer.strip())

    if use_tables:
        for tbl in tables:
            if len(tbl["content"]) < 300:
                continue
            desc = _describe_table_llm(tbl["content"])
            if desc:
                chunks.append(desc)

    return chunks


def extract_themes_from_docx(docx_path: str) -> List[str]:
    """
    Extract thematic blocks from a DOCX document.

    Args:
        docx_path (str): Path to the DOCX file.

    Returns:
        List[str]: Extracted non-empty sections of the document.
    """
    try:
        doc = Document(docx_path)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        raw_blocks = re.split(r"\r?\n\r?\n+", full_text)
        return [
            b.strip()
            for b in raw_blocks
            if b.strip() and not re.fullmatch(r"[a-zA-Zа-яА-Я0-9]+", b.strip())
        ]
    except Exception as e:
        print(f"Error reading DOCX file {docx_path}: {e}")
        return []


def extract_all_text(root_dir: str, use_tables: bool) -> List[str]:
    """
    Extract all relevant content from PDFs and DOCX files within a directory.

    Args:
        root_dir (str): Root directory to scan.
        use_tables (bool): Whether to include LLM-based table summaries.

    Returns:
        List[str]: List of extracted and processed text chunks.
    """
    if not Path(root_dir).exists():
        print(f"[!] Directory not found: {root_dir}")
        return []

    documents: List[str] = []

    pdf_files = list(Path(root_dir).rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files in {root_dir}")
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        try:
            chunks = extract_text_and_tables(str(pdf_file), use_tables)
            for chunk in chunks:
                documents.append(f"Document {pdf_file.name} contains:\n{chunk}")
        except Exception as e:
            print(f"Error reading PDF {pdf_file}: {e}")

    docx_files = list(Path(root_dir).rglob("*.docx"))
    print(f"Found {len(docx_files)} DOCX files in {root_dir}")
    for docx_file in tqdm(docx_files, desc="Processing DOCX"):
        documents.extend(extract_themes_from_docx(str(docx_file)))

    return documents
