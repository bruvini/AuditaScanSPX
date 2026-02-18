from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class MedicalRequest:
    patient_name: str
    birth_date: str
    request_date: str
    doctor_name: str
    procedure_name: str
    procedure_code: str

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Converts the dataclass to the legacy dictionary format expected by the Streamlit app."""
        return {
            "Paciente": self.patient_name,
            "Nascimento": self.birth_date,
            "Data Solicitação": self.request_date,
            "Médico Solicitante": self.doctor_name,
            "Procedimento": self.procedure_name,
            "Código": self.procedure_code
        }
