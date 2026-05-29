import json
from fastapi import APIRouter, HTTPException, Query, Depends
from database import get_db
from auth import get_current_user
from models.patient import PatientCreate
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from services.alert_service import process_analysis


class PatientSetup(BaseModel):
    name: str
    age: int
    gender: str
    phone: str

class PatientDoctorAssign(BaseModel):
    doctor_name: str
    doctor_phone: str
    doctor_whatsapp: Optional[str] = None


router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.post("")
async def create_patient(data: PatientCreate, user=Depends(get_current_user)):
    db = get_db()
    existing = await db.patients.find_one({"phone": data.phone})
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this phone already exists")
    patient = {
        "name": data.name,
        "age": data.age,
        "gender": data.gender,
        "phone": data.phone,
        "referring_doctor_id": ObjectId(data.referring_doctor_id) if data.referring_doctor_id else None,
        "total_visits": 0,
        "last_visit": None,
        "created_at": datetime.utcnow(),
    }
    result = await db.patients.insert_one(patient)
    patient["id"] = str(result.inserted_id)
    return {"message": "Patient registered", "patient_id": str(result.inserted_id)}


@router.get("")
async def get_patients(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=500),
                       user=Depends(get_current_user)):
    db = get_db()
    skip = (page - 1) * limit
    cursor = db.patients.find().sort("created_at", -1).skip(skip).limit(limit)
    patients = await cursor.to_list(length=limit)
    total = await db.patients.count_documents({})
    return {
        "patients": [{"id": str(p.pop("_id")), **p} for p in patients],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/search")
async def search_patients(q: str = Query(""), user=Depends(get_current_user)):
    db = get_db()
    if not q:
        return {"patients": []}
    cursor = db.patients.find({"name": {"$regex": q, "$options": "i"}}).limit(20)
    patients = await cursor.to_list(length=20)
    return {"patients": [{"id": str(p.pop("_id")), **p} for p in patients]}


@router.post("/setup")
async def setup_patient(data: PatientSetup, user=Depends(get_current_user)):
    db = get_db()
    existing = await db.patients.find_one({"user_id": ObjectId(user["id"])})
    if existing:
        raise HTTPException(status_code=400, detail="Patient profile already exists")
    patient = {
        "user_id": ObjectId(user["id"]),
        "name": data.name,
        "age": data.age,
        "gender": data.gender,
        "phone": data.phone,
        "doctor_name": None,
        "doctor_phone": None,
        "doctor_whatsapp": None,
        "total_visits": 0,
        "last_visit": None,
        "created_at": datetime.utcnow(),
    }
    result = await db.patients.insert_one(patient)
    return {"message": "Patient profile created", "patient_id": str(result.inserted_id)}


@router.get("/me")
async def get_my_profile(user=Depends(get_current_user)):
    db = get_db()
    patient = await db.patients.find_one({"user_id": ObjectId(user["id"])})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found. Please complete setup.")
    reports = await db.reports.find({"patient_id": patient["_id"]}).sort("uploaded_at", -1).to_list(length=50)
    patient["id"] = str(patient["_id"])
    return {
        "patient": patient,
        "reports": [{"id": str(r.pop("_id")), **r} for r in reports],
        "total_reports": len(reports),
    }


@router.post("/doctor")
async def assign_doctor(data: PatientDoctorAssign, user=Depends(get_current_user)):
    db = get_db()
    patient = await db.patients.find_one({"user_id": ObjectId(user["id"])})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    await db.patients.update_one(
        {"_id": patient["_id"]},
        {"$set": {
            "doctor_name": data.doctor_name,
            "doctor_phone": data.doctor_phone,
            "doctor_whatsapp": data.doctor_whatsapp,
        }},
    )
    return {"message": "Doctor details saved"}


@router.post("/retry-alerts")
async def retry_pending_alerts(user=Depends(get_current_user)):
    db = get_db()
    patient = await db.patients.find_one({"user_id": ObjectId(user["id"])})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    if not patient.get("doctor_whatsapp"):
        raise HTTPException(status_code=400, detail="No doctor contact saved. Please add your doctor first.")

    pending = await db.reports.find({
        "patient_id": patient["_id"],
        "is_critical": True,
        "alert_status": {"$in": ["no_doctor", "none", "pending"]},
    }).to_list(length=20)

    results = []
    for report in pending:
        vision_raw = report.get("nvidia_vision_raw")
        if vision_raw:
            vision_result = json.loads(vision_raw)
            alert_result = await process_analysis(str(report["_id"]), str(patient["_id"]), vision_result)
            results.append({"report_id": str(report["_id"]), "status": alert_result.get("status")})

    return {"sent": len(results), "results": results}


@router.get("/{patient_id}")
async def get_patient(patient_id: str, user=Depends(get_current_user)):
    db = get_db()
    patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    reports = await db.reports.find({"patient_id": ObjectId(patient_id)}).sort("uploaded_at", -1).to_list(length=50)
    patient["id"] = str(patient["_id"])
    return {
        "patient": patient,
        "reports": [{"id": str(r.pop("_id")), **r} for r in reports],
        "total_reports": len(reports),
    }
