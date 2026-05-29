from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertResponse(BaseModel):
    id: str
    report_id: str
    patient_id: str
    doctor_id: str
    alert_type: str  # "auto" or "manual"
    message_sent: str
    status: str  # "sent", "failed", "pending", "acknowledged", "resolved"
    whatsapp_status: Optional[str] = None  # "sent" or "failed"
    whatsapp_sid: Optional[str] = None  # Twilio message SID
    contact_method: str = "whatsapp"
    escalation_count: int = 0
    escalation_target: Optional[str] = None
    escalation_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
