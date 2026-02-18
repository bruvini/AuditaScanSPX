import logging
import re
from typing import List
from .io import PDFReader
from .extractors import PatientExtractor, DateExtractor, DoctorExtractor, ProcedureExtractor
from .models import MedicalRequest

# Configure logger
logger = logging.getLogger(__name__)

class OCRPipeline:
    def process(self, pdf_path: str) -> List[MedicalRequest]:
        """
        Main pipeline method to process a scanned PDF and extract medical requests.
        """
        logger.info(f"Starting OCR pipeline for: {pdf_path}")

        extracted_requests: List[MedicalRequest] = []
        pages_text = PDFReader.extract_text(pdf_path)

        if not pages_text:
            logger.warning(f"No text extracted from {pdf_path}")
            return []

        for page_num, text in enumerate(pages_text, 1):
            logger.debug(f"Processing page {page_num}")

            # --- 1. PATIENT ---
            patient_name = PatientExtractor.extract(text)

            # --- 2. BIRTH DATE ---
            # Label: 6-Data nasc or Data nasc
            birth_date_label = r"(?:6\s*[-–]\s*)?D\s*a\s*t\s*a\s*n\s*a\s*s\s*c"
            birth_date = DateExtractor.extract(text, birth_date_label)

            # --- 3. REQUEST DATE ---
            # Label: Data sol
            request_date_label = r"D\s*a\s*t\s*a\s*s\s*o\s*l"
            request_date = DateExtractor.extract(text, request_date_label)

            # Fallback for Request Date
            if request_date == "NÃO DETECTADO":
                rescue_anchors = [
                    r"C\s*i\s*d\s*c\s*a\s*u\s*s\s*a\s*s",
                    r"N\s*ú\s*m\s*e\s*r\s*o\s*d\s*o\s*c",
                    r"C\s*N\s*S",
                    r"A\s*U\s*T\s*O\s*R\s*I\s*Z\s*A"
                ]
                for anchor in rescue_anchors:
                    candidate_date = DateExtractor.extract(text, anchor, search_window=80)
                    if candidate_date != "NÃO DETECTADO" and candidate_date != birth_date:
                        request_date = candidate_date
                        break

            # --- 4. DOCTORS ---
            doctor_name = DoctorExtractor.extract(text)

            # --- 5. PROCEDURES ---
            procedures = ProcedureExtractor.extract(text)

            if procedures:
                for code, proc_name in procedures:
                    req = MedicalRequest(
                        patient_name=patient_name,
                        birth_date=birth_date,
                        request_date=request_date,
                        doctor_name=doctor_name,
                        procedure_name=proc_name,
                        procedure_code=code
                    )
                    extracted_requests.append(req)
            else:
                # If no procedure found, add a placeholder entry to indicate failure but preserve other data
                req = MedicalRequest(
                    patient_name=patient_name,
                    birth_date=birth_date,
                    request_date=request_date,
                    doctor_name=doctor_name,
                    procedure_name="NÃO ENCONTRADO (OCR Falhou)",
                    procedure_code=""
                )
                extracted_requests.append(req)

        logger.info(f"Extraction complete. Found {len(extracted_requests)} requests.")
        return extracted_requests

def run_pipeline(pdf_path: str) -> List[MedicalRequest]:
    pipeline = OCRPipeline()
    return pipeline.process(pdf_path)
