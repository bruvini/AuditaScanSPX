import re
from typing import List, Tuple, Optional, Set
from difflib import SequenceMatcher
from .cleaners import (
    validate_and_clean_procedure,
    normalize_for_comparison,
    clean_patient_name,
    clean_doctor_name,
    repair_fragmented_text
)

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

class DateExtractor:
    @staticmethod
    def extract(text: str, label_pattern: str, search_window: int = 50) -> str:
        """
        Extracts a date following a label, handling OCR errors by mapping common character misinterpretations.
        """
        match_label = re.search(label_pattern, text, re.IGNORECASE | re.VERBOSE)
        if not match_label:
            return "NÃO DETECTADO"

        start = match_label.end()
        raw_segment = text[start : start + search_window]

        # OCR Correction Map for dates
        ocr_map = {
            'O': '0', 'D': '0', 'Q': '0', 'U': '0',
            'L': '1', 'I': '1', '|': '1', 'l': '1', '/': '1', '\\': '1',
            'Z': '2', 'E': '3', 'A': '4', 'S': '5',
            'G': '6', 'b': '6', 'T': '7', 'B': '8'
        }

        clean_segment = raw_segment.upper().replace(" ", "")
        reconstructed_chars = []
        for char in clean_segment:
            if char.isdigit():
                reconstructed_chars.append(char)
            elif char in ['/', '.', '-']:
                reconstructed_chars.append('/')
            elif char in ocr_map:
                reconstructed_chars.append(ocr_map[char])

        reconstructed_text = "".join(reconstructed_chars)
        match_date = re.search(r'(\d{2})/(\d{2})/(\d{4})', reconstructed_text)

        if match_date:
            return f"{match_date.group(1)}/{match_date.group(2)}/{match_date.group(3)}"

        return "NÃO DETECTADO"

class ProcedureExtractor:
    @staticmethod
    def extract(text: str) -> List[Tuple[str, str]]:
        """
        Extracts procedures and their codes. Returns a list of (code, description) tuples.
        """
        procedures: List[Tuple[str, str]] = []

        # --- STRATEGY 1: Search by CODE (High Confidence) ---
        # Pattern: digits followed by text, stopping at Qtd, Justification or CID
        code_regex = re.compile(r"""
            ((?:\d\s*){7,15})       # Group 1: The code (digits with spaces)
            \s*[-–]?\s*             # Separator
            ([^\d]+?)               # Group 2: The description (non-digits)
            (?=\s*Q(?:td|TD)        # Lookahead: Stop at Qtd
            |\s*JUSTIFICATIVA       # or JUSTIFICATIVA
            |\s*CID)                # or CID
        """, re.VERBOSE | re.IGNORECASE)

        matches_code = code_regex.findall(text)

        for dirty_code, desc in matches_code:
            clean_code = re.sub(r'\s+', '', dirty_code)
            valid_desc = validate_and_clean_procedure(desc)

            if valid_desc and len(clean_code) >= 7:
                procedures.append((clean_code, valid_desc))

        # --- STRATEGY 2: Search by LABEL (Fallback) ---
        # Pattern: words ending in 'to' (like 'Procedimento') followed by description
        text_regex = re.compile(r"""
            (?:[a-zA-Z\s]{1,20})    # Prefix words
            [tT]\s*[oO]\s*[-–]?\s*  # Ends in 'to' (e.g. ProcedimenTO) + separator
            ([A-Z\s/ÁÉÍÓÚÇÃÕ\-\(\)]{5,150}?) # Group 1: The description
            (?=\s*Q(?:td|TD))       # Lookahead: Stop at Qtd
        """, re.VERBOSE | re.IGNORECASE)

        matches_text = text_regex.findall(text)

        for desc in matches_text:
            valid_desc = validate_and_clean_procedure(desc)

            if valid_desc:
                # Deduplication logic
                norm_new = normalize_for_comparison(valid_desc)
                is_duplicate = False

                for _, existing in procedures:
                    norm_existing = normalize_for_comparison(existing)

                    # 1. Substring check
                    if norm_new in norm_existing:
                        is_duplicate = True
                        break

                    # 2. Reverse substring check (prefer existing if it contains new)
                    if norm_existing in norm_new:
                        is_duplicate = True
                        break

                    # 3. High similarity check
                    if similarity(norm_new, norm_existing) > 0.75:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    procedures.append(("", valid_desc))

        return procedures

class PatientExtractor:
    @staticmethod
    def extract(text: str) -> str:
        # Strategy 1: Explicit label "Paciente"
        patient_pattern = re.compile(r"""
            (?:3\s*[-–._]?\s*)?     # Optional number prefix "3 - "
            P\s*a\s*c\s*i\s*e\s*n\s*t\s*e\s+ # "Paciente" with optional spaces
            (.{5,100})              # The name
        """, re.VERBOSE | re.IGNORECASE)

        match = patient_pattern.search(text)
        if match:
            return clean_patient_name(match.group(1))

        # Strategy 2: Fallback based on position relative to other fields (CNS, Data)
        rescue_pattern = re.compile(r"""
            (.{10,120}?)            # Candidate name text
            \s+                     # Separator
            (?:5\s*-\s*CNS|CNS\s*\d|6\s*-\s*Data) # Followed by CNS or Data label
        """, re.VERBOSE | re.IGNORECASE)

        match_rescue = rescue_pattern.search(text)
        if match_rescue:
            candidate = match_rescue.group(1).strip()
            # Clean up common garbage prefixes in rescue mode
            if "SOLICITANTE" in candidate.upper():
                candidate = re.split(r'SOLICITANTE\)', candidate, flags=re.IGNORECASE)[-1]
            elif "SAÚDE" in candidate.upper():
                candidate = re.split(r'SAÚDE', candidate, flags=re.IGNORECASE)[-1]
            return clean_patient_name(candidate)

        return "NÃO DETECTADO"

class DoctorExtractor:
    @staticmethod
    def extract(text: str) -> str:
        candidates = []

        # 1. "Solicitante" label
        match_solic = re.search(r"S\s*o\s*l\s*i\s*c\s*i\s*t\s*a\s*n\s*t\s*e\s+(.*?)(?:\s-\s|CRM|Data|CNES|CPF|\d{2}/\d{2})", text, re.IGNORECASE)
        if match_solic:
            cleaned = clean_doctor_name(match_solic.group(1))
            if cleaned: candidates.append(cleaned)

        # 2. "Responsável" label
        match_resp = re.search(r"R\s*e\s*s\s*p\s*o\s*n\s*s\s*á\s*v\s*e\s*l\s*.*?\s*d\s*o\s*c\s*u\s*m\s*e\s*n\s*t\s*o\s+(.*?)(?:\s-\s|CRM|Data|:)", text, re.IGNORECASE)
        if match_resp:
            cleaned = clean_doctor_name(match_resp.group(1))
            if cleaned: candidates.append(cleaned)

        # Deduplicate and Join
        final_doctors: List[str] = []
        for doc in candidates:
            is_new = True
            for existing in final_doctors:
                if similarity(doc, existing) > 0.85 or doc in existing or existing in doc:
                    is_new = False
                    break
            if is_new:
                final_doctors.append(doc)

        return " / ".join(final_doctors) if final_doctors else "NÃO DETECTADO"
