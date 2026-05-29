from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import get_current_user
from models.doctor import DoctorCreate, DoctorUpdate
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class DoctorSetup(BaseModel):
    name: str
    phone: str
    whatsapp_number: str
    specialization: str
    backup_contact: Optional[str] = None


router = APIRouter(prefix="/api/v1/doctors", tags=["doctors"])


@router.post("/setup")
async def setup_doctor(data: DoctorSetup, user=Depends(get_current_user)):
    db = get_db()
    existing = await db.doctors.find_one({"user_id": ObjectId(user["id"])})
    if existing:
        raise HTTPException(status_code=400, detail="Doctor profile already exists")
    doctor = {
        "user_id": ObjectId(user["id"]),
        "name": data.name,
        "phone": data.phone,
        "whatsapp_number": data.whatsapp_number,
        "specialization": data.specialization,
        "backup_contact": data.backup_contact,
        "total_referrals": 0,
        "created_at": datetime.utcnow(),
    }
    result = await db.doctors.insert_one(doctor)
    doctor["id"] = str(result.inserted_id)
    return {"message": "Doctor profile created", "doctor_id": str(result.inserted_id)}


@router.post("")
async def create_doctor(data: DoctorCreate, user=Depends(get_current_user)):
    db = get_db()
    doctor = {
        "name": data.name,
        "phone": data.phone,
        "whatsapp_number": data.whatsapp_number,
        "specialization": data.specialization,
        "backup_contact": data.backup_contact,
        "total_referrals": 0,
        "created_at": datetime.utcnow(),
    }
    result = await db.doctors.insert_one(doctor)
    return {"message": "Doctor added", "doctor_id": str(result.inserted_id)}


@router.get("/me")
async def get_my_doctor_profile(user=Depends(get_current_user)):
    db = get_db()
    doctor = await db.doctors.find_one({"user_id": ObjectId(user["id"])})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    doctor["id"] = str(doctor["_id"])
    return {"doctor": doctor}


@router.get("")
async def get_doctors(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.doctors.find().sort("name", 1)
    doctors = await cursor.to_list(length=100)
    return {"doctors": [{"id": str(d.pop("_id")), **d} for d in doctors]}


@router.get("/{doctor_id}")
async def get_doctor(doctor_id: str, user=Depends(get_current_user)):
    db = get_db()
    doctor = await db.doctors.find_one({"_id": ObjectId(doctor_id)})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor["id"] = str(doctor["_id"])
    return {"doctor": doctor}


@router.put("/{doctor_id}")
async def update_doctor(doctor_id: str, data: DoctorUpdate, user=Depends(get_current_user)):
    db = get_db()
    update = {k: v for k, v in data.dict().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.doctors.update_one({"_id": ObjectId(doctor_id)}, {"$set": update})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"message": "Doctor updated"}
