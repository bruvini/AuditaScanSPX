import logging
from typing import List, Optional
from .cleaners import clean_ocr_text

logger = logging.getLogger(__name__)

class PDFReader:
    @staticmethod
    def extract_text(pdf_path: str) -> List[str]:
        """
        Reads a PDF file and returns a list of cleaned text strings, one per page.
        """
        import pdfplumber

        pages_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    raw_text = page.extract_text()
                    if raw_text:
                        cleaned = clean_ocr_text(raw_text)
                        if cleaned:
                            pages_text.append(cleaned)
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            return []

        return pages_text
