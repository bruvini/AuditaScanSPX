from typing import List, Dict, Any
from .ocr_pipeline.pipeline import OCRPipeline

def extrair_dados_solicitacao(caminho_pdf: str) -> List[Dict[str, Any]]:
    """
    Facade function to maintain backward compatibility with the existing Streamlit app.
    Delegates the processing to the new OCRPipeline and converts the result to the legacy format.
    """
    pipeline = OCRPipeline()
    extracted_requests = pipeline.process(caminho_pdf)
    return [req.to_legacy_dict() for req in extracted_requests]
