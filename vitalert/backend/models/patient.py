from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    phone: str
    referring_doctor_id: Optional[str] = None


class PatientResponse(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    phone: str
    referring_doctor_id: Optional[str] = None
    total_visits: int = 0
    last_visit: Optional[datetime] = None
    created_at: datetime
