"""
Phase 2.1 - Source ingestion and cleanup for professor materials.

Supports PDF, DOCX, and TXT.
Attempts OCR fallback for scanned PDFs when direct extraction is too weak.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import unicodedata
from pathlib import Path


def _extract_pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def _extract_pdf_text(path: Path) -> str:
    return "\n".join(_extract_pdf_pages(path))


def _extract_pdf_text_ocr(path: Path) -> str:
    # Optional OCR fallback for scanned PDFs.
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(str(path))
    pages = [pytesseract.image_to_string(img) for img in images]
    return "\n".join(pages)


def extract_pdf_pages_text(file_path: str, enable_ocr_fallback: bool = False) -> tuple[list[str], str]:
    """
    Returns (page_texts, extraction_mode) for PDFs.
    extraction_mode can be: pdf, pdf_ocr, unsupported.
    """
    path = Path(file_path)
    if path.suffix.lower() != ".pdf":
        return [], "unsupported"

    page_texts = _extract_pdf_pages(path)
    direct_text = "\n".join(page_texts)
    if enable_ocr_fallback and len(direct_text.strip()) < 300:
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(str(path))
            ocr_pages = [pytesseract.image_to_string(img) for img in images]
            ocr_text = "\n".join(ocr_pages)
            if len(ocr_text.strip()) > len(direct_text.strip()):
                return ocr_pages, "pdf_ocr"
        except Exception:
            pass

    return page_texts, "pdf"


def _extract_docx_text(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def extract_raw_text(file_path: str, enable_ocr_fallback: bool = True) -> tuple[str, str]:
    """
    Returns (raw_text, extraction_mode).
    extraction_mode can be: pdf, pdf_ocr, docx, txt.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        raw = _extract_pdf_text(path)
        # If almost empty, attempt OCR fallback.
        if enable_ocr_fallback and len((raw or "").strip()) < 300:
            try:
                ocr_text = _extract_pdf_text_ocr(path)
                if len((ocr_text or "").strip()) > len((raw or "").strip()):
                    return ocr_text, "pdf_ocr"
            except Exception:
                # Keep direct extraction if OCR stack is unavailable/fails.
                pass
        return raw, "pdf"

    if suffix == ".docx":
        return _extract_docx_text(path), "docx"

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore"), "txt"

    raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX, TXT, or MD.")


def clean_text(raw_text: str) -> str:
    """Normalize noisy extraction output while preserving paragraph boundaries."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Repair line-break hyphenation: compu-\nter -> computer
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Drop standalone page-number lines.
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    lines = [ln.strip() for ln in text.split("\n")]
    # Remove repetitive short header/footer lines.
    freq: dict[str, int] = {}
    for ln in lines:
        if not ln:
            continue
        key = re.sub(r"\s+", " ", ln)
        freq[key] = freq.get(key, 0) + 1

    cleaned_lines: list[str] = []
    for ln in lines:
        if not ln:
            cleaned_lines.append("")
            continue
        norm = re.sub(r"\s+", " ", ln)
        if len(norm) <= 80 and freq.get(norm, 0) >= 3:
            continue
        cleaned_lines.append(norm)

    text = "\n".join(cleaned_lines)
    text = unicodedata.normalize("NFKC", text)

    # Preserve paragraph boundaries while normalizing noisy spacing.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_ocr_environment_status() -> dict:
    """Return a readiness snapshot for optional OCR fallback dependencies."""
    pdf2image_available = importlib.util.find_spec("pdf2image") is not None
    pytesseract_available = importlib.util.find_spec("pytesseract") is not None
    poppler_available = bool(shutil.which("pdftoppm") or shutil.which("pdfinfo"))
    tesseract_cmd = shutil.which("tesseract")

    return {
        "pdf2image_available": pdf2image_available,
        "pytesseract_available": pytesseract_available,
        "poppler_available": poppler_available,
        "tesseract_available": bool(tesseract_cmd),
        "tesseract_cmd": tesseract_cmd,
        "ocr_ready": all([
            pdf2image_available,
            pytesseract_available,
            poppler_available,
            bool(tesseract_cmd),
        ]),
    }
