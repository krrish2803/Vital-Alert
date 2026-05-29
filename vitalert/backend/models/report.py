from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ReportFile(BaseModel):
    filename: str
    file_path: str
    file_type: str
    page_count: int = 1
    file_size: int = 0


class ExtractedValue(BaseModel):
    test_name: str
    value: float
    unit: str
    normal_range: str
    status: str


class ReportResponse(BaseModel):
    id: str
    patient_id: str
    report_type: str
    files: List[ReportFile] = []
    nvidia_vision_raw: Optional[str] = None
    extracted_values: List[ExtractedValue] = []
    health_summary: Optional[str] = None
    critical_findings: List[str] = []
    is_critical: bool = False
    confidence_score: float = 0.0
    severity: str = "normal"
    requires_human_review: bool = False
    suggested_action: Optional[str] = None
    alert_status: Optional[str] = None
    uploaded_by: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
