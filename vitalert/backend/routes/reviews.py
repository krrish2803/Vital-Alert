import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from database import get_db
from auth import get_current_user
from services.whatsapp_service import send_whatsapp
from config import FRONTEND_URL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.get("")
async def list_pending_reviews(page: int = 1, limit: int = 20, user=Depends(get_current_user)):
    db = get_db()
    skip = (page - 1) * limit
    query = {"requires_human_review": True}
    cursor = db.reports.find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
    reports = await cursor.to_list(length=limit)
    total = await db.reports.count_documents(query)

    enriched = []
    for r in reports:
        r["id"] = str(r["_id"])
        patient = await db.patients.find_one({"_id": r["patient_id"]})
        if patient:
            r["patient_name"] = patient.get("name", "Unknown")
            r["patient_age"] = patient.get("age")
            r["patient_gender"] = patient.get("gender")
        else:
            r["patient_name"] = "Unknown"
        enriched.append(r)

    return {"reviews": enriched, "total": total, "page": page, "pages": (total + limit - 1) // limit}


@router.get("/{report_id}")
async def get_review_detail(report_id: str, user=Depends(get_current_user)):
    db = get_db()
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report["id"] = str(report["_id"])

    patient = await db.patients.find_one({"_id": report["patient_id"]})
    doctor = None
    if patient:
        patient["id"] = str(patient["_id"])
        if patient.get("referring_doctor_id"):
            doctor = await db.doctors.find_one({"_id": patient["referring_doctor_id"]})
            if doctor:
                doctor["id"] = str(doctor["_id"])

    return {
        "report": report,
        "patient": patient,
        "doctor": doctor,
    }


@router.post("/{report_id}/approve")
async def approve_review(report_id: str, data: dict = {}, user=Depends(get_current_user)):
    db = get_db()
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.get("requires_human_review"):
        raise HTTPException(status_code=400, detail="Report does not require review")

    patient = await db.patients.find_one({"_id": report["patient_id"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor_id = patient.get("referring_doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=400, detail="No referring doctor for this patient")

    doctor = await db.doctors.find_one({"_id": doctor_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Referring doctor not found")

    vision_data = {}
    try:
        vision_data = json.loads(report.get("nvidia_vision_raw", "{}"))
    except (json.JSONDecodeError, Exception):
        pass

    now = datetime.utcnow()
    time_str = now.strftime("%I:%M:%S %p")
    critical_findings_text = "\n".join(vision_data.get("critical_findings", [])) or "Critical values detected"
    health_summary = report.get("health_summary", "")
    suggested_action = vision_data.get("suggested_action", "")

    msg = (
        f"🚨 CRITICAL ALERT — VitalAlert (Approved by staff)\n\n"
        f"Patient: {patient['name']}, {patient['age']}{patient['gender'][0]}\n"
        f"Report: {report.get('report_type', 'Report')}\n"
        f"Time: {time_str}\n\n"
        f"⚠️ Critical Findings:\n{critical_findings_text}\n\n"
        f"AI Summary:\n{health_summary}\n\n"
        f"Suggested Action:\n{suggested_action}\n\n"
        f"— VitalAlert System"
    )

    whatsapp_result = await send_whatsapp(doctor["whatsapp_number"], msg)
    sent = whatsapp_result["success"]

    alert_doc = {
        "report_id": ObjectId(report_id),
        "patient_id": report["patient_id"],
        "doctor_id": doctor_id,
        "alert_type": "manual",
        "message_sent": msg,
        "status": "sent" if sent else "failed",
        "whatsapp_status": "sent" if sent else "failed",
        "whatsapp_sid": whatsapp_result["sid"] if sent else None,
        "contact_method": "whatsapp",
        "escalation_count": 0,
        "sent_at": now,
    }
    alert_result = await db.alerts.insert_one(alert_doc)

    notes = data.get("notes", "")
    await db.reports.update_one(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "requires_human_review": False,
                "alert_status": "sent" if sent else "failed",
                "review_action": "approved",
                "reviewed_by": user.get("email", "staff"),
                "reviewed_at": now,
                "review_notes": notes,
            }
        },
    )

    logger.info(f"Review approved for report {report_id}. Alert {'sent' if sent else 'failed'}")
    return {
        "message": "Report approved. Doctor alerted." if sent else "Report approved. WhatsApp failed.",
        "alert_sent": sent,
        "alert_id": str(alert_result.inserted_id),
    }


@router.post("/{report_id}/reject")
async def reject_review(report_id: str, data: dict = {}, user=Depends(get_current_user)):
    db = get_db()
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.get("requires_human_review"):
        raise HTTPException(status_code=400, detail="Report does not require review")

    notes = data.get("notes", "")
    now = datetime.utcnow()

    await db.reports.update_one(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "requires_human_review": False,
                "alert_status": "false_alarm",
                "review_action": "rejected",
                "reviewed_by": user.get("email", "staff"),
                "reviewed_at": now,
                "review_notes": notes,
            }
        },
    )

    logger.info(f"Review rejected for report {report_id}: {notes}")
    return {"message": "Report rejected (false alarm)"}
