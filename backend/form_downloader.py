# form_downloader.py – Official PDF download and fill/overlay

"""Utility that knows how to download a government form PDF for a given process
and either fill the existing fields (if it is a fillable PDF) or overlay the
user data on a separate cover page.

The module maintains a curated map of processes -> official PDF URLs. When the
requested process is not in the map we fall back to a generic search (similar to
link_fetcher) – the caller can decide whether to use the generic URL or ask the
user to provide a PDF.
"""

import os
import io
import requests
from typing import Dict, List

# Optional: for PDF manipulation
try:
    from pypdf import PdfReader, PdfWriter
    PDF_LIB = "pypdf"
except ImportError:
    PDF_LIB = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Curated map of process name (lowercase) -> official PDF URLs
KNOWN_FORMS: Dict[str, str] = {
    "passport": "https://www.passportindia.gov.in/AppOnlineProject/pdf/GEP_Booklet.pdf",
    "birth_certificate": "https://crvsup.nhp.gov.in/pdf/birth_certificate_form.pdf",
    # Add more as needed
}

def _download_pdf(url: str) -> bytes:
    """Download a PDF from *url* and return its raw bytes.
    Raises an exception on network errors or non‑PDF content.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    if "application/pdf" not in resp.headers.get("Content-Type", ""):
        # Some gov sites serve PDF with generic mime – still accept if starts with %PDF
        if not resp.content.startswith(b"%PDF"):
            raise ValueError("URL does not point to a PDF file")
    return resp.content

def _fill_pdf(fillable_bytes: bytes, data: Dict[str, str]) -> bytes:
    """Fill a *fillable* PDF using pypdf.
    *data* is a mapping of field name -> value.
    Returns the new PDF as bytes.
    """
    if PDF_LIB != "pypdf":
        raise RuntimeError("pypdf is required for fillable PDFs")
    reader = PdfReader(io.BytesIO(fillable_bytes))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    if not writer.get_fields():
        raise ValueError("PDF has no fillable fields")
    # Update fields (simple first‑page approach)
    for field, value in data.items():
        if field in writer.get_fields():
            writer.update_page_form_field_values(writer.pages[0], {field: value})
    out_stream = io.BytesIO()
    writer.write(out_stream)
    return out_stream.getvalue()

def _overlay_pdf(original_bytes: bytes, data: Dict[str, str]) -> bytes:
    """Create a single‑page cover sheet with the *data* and prepend it to the
    original PDF. Uses reportlab to draw the key/value pairs.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required for overlay PDFs")
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    y = 750
    can.setFont("Helvetica-Bold", 12)
    can.drawString(50, y, "Auto‑filled Form Data")
    y -= 30
    can.setFont("Helvetica", 10)
    for key, value in data.items():
        can.drawString(50, y, f"{key}: {value}")
        y -= 20
    can.save()
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    original_reader = PdfReader(io.BytesIO(original_bytes))
    writer = PdfWriter()
    writer.add_page(overlay_reader.pages[0])
    for page in original_reader.pages:
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

def get_official_form(topic: str, user_data: Dict[str, str]) -> bytes:
    """Main entry point.
    *topic* – e.g. "passport" or "birth_certificate".
    *user_data* – dictionary of field name/value extracted from the conversation.
    Returns a PDF (bytes) ready for download.
    """
    topic_key = topic.lower().replace(" ", "_")
    url = KNOWN_FORMS.get(topic_key)
    if not url:
        raise ValueError(f"No known official form for topic '{topic}'. Provide a custom URL.")
    raw_pdf = _download_pdf(url)
    try:
        # Try to fill if the PDF is fillable
        return _fill_pdf(raw_pdf, user_data)
    except Exception:
        # Fallback to overlay method
        return _overlay_pdf(raw_pdf, user_data)
