import re
from typing import Optional, List

def repair_fragmented_text(text: str) -> str:
    """
    Repairs text with fragmented characters (e.g., "A R A U J O" -> "ARAUJO").
    """
    if not text:
        return ""
    # Join single uppercase letters separated by spaces
    text = re.sub(r'\b([A-Z])\s+(?=[A-Z]\b)', r'\1', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_ocr_text(text: str) -> str:
    """
    General cleaning for OCR output: removes control characters and normalizes whitespace.
    """
    if not text:
        return ""
    text = text.replace('\n', ' ')
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def normalize_for_comparison(text: str) -> str:
    """
    Removes spaces and punctuation for robust string comparison.
    Example: 'TOMOGRAFIA' matches 'T O M O GRAFIA'
    """
    if not text:
        return ""
    return re.sub(r'[\W_]+', '', text.upper())

def clean_patient_name(raw_name: str) -> str:
    """
    Cleans and extracts the patient name from a raw extracted string.
    Removes headers, labels, and trailing garbage.
    """
    if not raw_name:
        return "NÃO DETECTADO"

    repaired_name = repair_fragmented_text(raw_name)
    upper_text = repaired_name.upper()

    # List of markers that indicate the end of the name field
    end_markers = [
        "4-PRONT", "PRONTUÁRIO", "PRONTUARIO", "PRONT",
        "5-CNS", "5- CNS", "CNS", "CARTÃO",
        "6-DATA", "DATA NASC", "DT NASC",
        "7-SEXO", "SEXO",
        "8-RAÇA", "RACA", "COR",
        "9-MÃE", "MAE",
        "10-FONE", "FONE",
        "CF:S", "COMENTOS", "14-PRONT", "1Ï~", "1DSCILINO"
    ]

    # Find the earliest occurrence of an end marker
    cutoff_index = len(upper_text)
    for marker in end_markers:
        idx = upper_text.find(marker)
        if idx != -1 and idx < cutoff_index:
            cutoff_index = idx

    clean_name = repaired_name[:cutoff_index].strip()

    # Remove common prefixes/labels
    clean_name = re.sub(r'^.*(?:IDENTIFICAÇÃO|ESTABELECIMENTO|SOLICITANTE\)|SAÚDE)\s*', '', clean_name, flags=re.IGNORECASE)

    # Remove numbers if they appear (often ID numbers leaking in)
    match_number = re.search(r'\d{3,}', clean_name)
    if match_number:
        clean_name = clean_name[:match_number.start()].strip()

    # Remove leading/trailing non-alphanumeric chars
    clean_name = re.sub(r'^[\d\W_]+', '', clean_name)
    clean_name = re.sub(r'[\d\W_]+$', '', clean_name)

    if len(clean_name) < 3:
        return "NÃO DETECTADO"

    return clean_name.upper()

def clean_doctor_name(name: str) -> str:
    """
    Cleans the doctor's name by removing CRM, dates, and other artifacts.
    """
    if not name:
        return ""

    # Split at common delimiters that follow the name
    name = re.split(r'(?:-|CRM|Data|Assinatura|CNES|CPF|\d{2}/\d{2}|:)', name, flags=re.IGNORECASE)[0]

    # Remove garbage characters
    name = re.sub(r'^[\d\W_]+', '', name)
    name = re.sub(r'[\\/|()0-9]', '', name)

    name = name.strip().upper()

    # Validation: name must be at least 3 chars and have some variety
    if len(name) < 3 or len(set(name)) == 1:
        return ""

    return name

def validate_and_clean_procedure(text: str) -> Optional[str]:
    """
    Validates and cleans a procedure description.
    Returns None if the text is invalid or corresponds to a blacklisted term.
    """
    if not text:
        return None

    clean_text = text.upper().strip()

    # --- 1. Footer Cutting ---
    # Patterns indicating the start of footer garbage
    footer_patterns = [
        r'\s*Q(?:td|TD).*$',          # Qtd
        r'G\s*O\s*N\s*T\s*O.*',       # Specific pattern "G O N T O"
        r'A\s*G\s*T\s*C.*',           # Specific pattern "A G T C"
        r'0\s*5\s*/\s*G.*'            # Weird line ending
    ]
    for pattern in footer_patterns:
        clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE).strip()

    # --- 2. Header Removal ---
    start_garbage_patterns = [
        r'^PROCEDIMENTO\s*SOLICITADO\s*[-–]?\s*',
        r'^PROCEDIMENTO\s*[-–]?\s*',
        r'^SOLICITADO\s*[-–]?\s*',
        r'^AGTC\s*',
        r'^\d+\s*[-–]\s*'
    ]
    for pattern in start_garbage_patterns:
        clean_text = re.sub(pattern, '', clean_text).strip()

    # --- 3. Strict Blacklist ---
    strict_blacklist = [
        "SOLICITADO", "PROCEDIMENTO", "QTD", "QTD PROCEDIMENTO",
        "AGTC", "A GTC", "MUNICIPIO", "JOINVILLE",
        "ESTABELECIMENTO", "SAUDE", "SUS", "PAGINA",
        "PROCEDIMENTO SOLICITADO", "MUNICIPIO JOINVILLE",
        "PROCEDIMENTO PROCEDIMENTO", "A GTC PROCEDIMENTO"
    ]

    if clean_text in strict_blacklist:
        return None

    # --- 4. "Contains" Blacklist ---
    contaminated_words = ["JOINVILLE", "MUNICIPIO", "AGTC", "ESTABELECIMENTO", "AUTORIZAÇÃO", "GTC"]
    for word in contaminated_words:
        # Only discard if the word is a significant part (surrounded by spaces)
        if f" {word} " in f" {clean_text} ":
            return None

    if "RUA" in clean_text or "BAIRRO" in clean_text or "CEP" in clean_text:
        return None

    if len(clean_text) < 5:
        return None

    return clean_text
