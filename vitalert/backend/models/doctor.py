from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DoctorCreate(BaseModel):
    name: str
    phone: str
    whatsapp_number: str
    specialization: str
    backup_contact: Optional[str] = None


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    specialization: Optional[str] = None
    backup_contact: Optional[str] = None


class DoctorResponse(BaseModel):
    id: str
    name: str
    phone: str
    whatsapp_number: str
    specialization: str
    backup_contact: Optional[str] = None
    total_referrals: int = 0
    created_at: datetime
