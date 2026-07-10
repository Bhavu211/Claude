"""Extract plain text from uploaded resume/JD files (PDF, DOCX, or plain text)."""

from __future__ import annotations

import io


class UnsupportedFileType(ValueError):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Dispatch by extension. Raises UnsupportedFileType for anything else —
    never silently returns empty text for a format we can't actually read."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    if ext == "docx":
        return extract_text_from_docx(file_bytes)
    if ext in ("txt", "md"):
        return file_bytes.decode("utf-8", errors="replace").strip()
    raise UnsupportedFileType(f"Unsupported file type '.{ext}' — upload a PDF, DOCX, or plain text file.")
