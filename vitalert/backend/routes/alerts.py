from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import get_current_user
from services.whatsapp_service import send_whatsapp
from services.alert_service import process_analysis
from bson import ObjectId
from datetime import datetime
from config import FRONTEND_URL, ALERT_CC_WHATSAPP
from pydantic import BaseModel
import json


class SendAlertRequest(BaseModel):
    report_id: str

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
async def get_alerts(page: int = 1, limit: int = 20, user=Depends(get_current_user)):
    db = get_db()
    skip = (page - 1) * limit
    cursor = db.alerts.find().sort("sent_at", -1).skip(skip).limit(limit)
    alerts = await cursor.to_list(length=limit)
    total = await db.alerts.count_documents({})

    enriched = []
    for alert in alerts:
        alert["id"] = str(alert["_id"])
        patient = await db.patients.find_one({"_id": alert["patient_id"]})
        doctor = await db.doctors.find_one({"_id": alert["doctor_id"]})
        if patient:
            alert["patient_name"] = patient.get("name")
        if doctor:
            alert["doctor_name"] = doctor.get("name")
        enriched.append(alert)

    return {"alerts": enriched, "total": total, "page": page, "pages": (total + limit - 1) // limit}


@router.get("/my")
async def get_my_alerts(user=Depends(get_current_user)):
    db = get_db()
    doctor = await db.doctors.find_one({"user_id": ObjectId(user["id"])})
    if not doctor:
        user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
        if user_doc and user_doc.get("name"):
            doctor = await db.doctors.find_one({"name": user_doc["name"]})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found. Please complete setup first.")
    cursor = db.alerts.find({
        "$or": [
            {"doctor_id": doctor["_id"]},
            {"doctor_name": doctor.get("name")},
        ]
    }).sort("sent_at", -1).limit(50)
    alerts = await cursor.to_list(length=50)
    enriched = []
    for alert in alerts:
        alert["id"] = str(alert["_id"])
        patient = await db.patients.find_one({"_id": alert["patient_id"]})
        report = await db.reports.find_one({"_id": alert["report_id"]})
        if patient:
            alert["patient_name"] = patient.get("name")
            alert["patient_age"] = patient.get("age")
            alert["patient_gender"] = patient.get("gender")
        if report:
            alert["report_type"] = report.get("report_type")
        enriched.append(alert)
    return {"alerts": enriched}


@router.get("/pending")
async def get_pending_alerts(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.alerts.find({"status": "sent"}).sort("sent_at", -1).limit(50)
    alerts = await cursor.to_list(length=50)
    return {"alerts": [{"id": str(a.pop("_id")), **a} for a in alerts]}


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    db = get_db()
    alert = await db.alerts.find_one({"_id": ObjectId(alert_id)})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert["id"] = str(alert["_id"])
    patient = await db.patients.find_one({"_id": alert["patient_id"]})
    doctor = await db.doctors.find_one({"_id": alert["doctor_id"]})
    report = await db.reports.find_one({"_id": alert["report_id"]})
    return {
        "alert": alert,
        "patient": {"id": str(patient.pop("_id")), **patient} if patient else None,
        "doctor": {"id": str(doctor.pop("_id")), **doctor} if doctor else None,
        "report": {"id": str(report.pop("_id")), **report} if report else None,
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user=Depends(get_current_user)):
    db = get_db()
    now = datetime.utcnow()
    result = await db.alerts.update_one(
        {"_id": ObjectId(alert_id)},
        {"$set": {"status": "acknowledged", "acknowledged_at": now}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert acknowledged", "status": "acknowledged"}


@router.post("/{alert_id}/message-patient")
async def message_patient(alert_id: str, data: dict, user=Depends(get_current_user)):
    db = get_db()
    alert = await db.alerts.find_one({"_id": ObjectId(alert_id)})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    patient = await db.patients.find_one({"_id": alert["patient_id"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    message = data.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    full_msg = f"VitalAlert - Message from your doctor:\n\n{message}"
    sent = await send_whatsapp(patient["phone"], full_msg)
    return {"message": "Message sent", "sent": sent}


@router.post("/manual-whatsapp")
async def manual_whatsapp(data: dict, user=Depends(get_current_user)):
    db = get_db()
    report_id = data.get("report_id")
    if not report_id:
        raise HTTPException(status_code=400, detail="report_id is required")

    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    patient = await db.patients.find_one({"_id": report["patient_id"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not patient.get("referring_doctor_id"):
        raise HTTPException(status_code=400, detail="No referring doctor for this patient")

    doctor = await db.doctors.find_one({"_id": patient["referring_doctor_id"]})
    if not doctor:
        raise HTTPException(status_code=404, detail="Referring doctor not found")

    vision_data = json.loads(report.get("nvidia_vision_raw", "{}"))
    critical_findings_text = "\n".join(vision_data.get("critical_findings", []))
    health_summary = report.get("health_summary", "")
    suggested_action = vision_data.get("suggested_action", "")

    msg = (
        f"*🚨 CRITICAL ALERT — VitalAlert*\n\n"
        f"*Patient:* {patient['name']}, {patient['age']}{patient['gender'][0]}\n"
        f"*Report:* {report['report_type']}\n"
        f"*Time:* {datetime.utcnow().strftime('%d %b %Y %I:%M %p')}\n\n"
        f"*⚠️ Critical Finding:*\n{critical_findings_text}\n\n"
        f"*AI Summary:*\n{health_summary}\n\n"
        f"*Suggested Action:* {suggested_action}\n\n"
        f"View & Acknowledge: {FRONTEND_URL}/portal/{report_id}\n\n"
        f"— VitalAlert System"
    )

    sent = await send_whatsapp(doctor["whatsapp_number"], msg)

    if ALERT_CC_WHATSAPP:
        await send_whatsapp(ALERT_CC_WHATSAPP, msg)

    alert_doc = {
        "report_id": ObjectId(report_id),
        "patient_id": report["patient_id"],
        "doctor_id": patient["referring_doctor_id"],
        "alert_type": "manual",
        "message_sent": msg,
        "status": "sent",
        "contact_method": "whatsapp",
        "escalation_count": 0,
        "sent_at": datetime.utcnow(),
    }
    alert_result = await db.alerts.insert_one(alert_doc)
    await db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": {"alert_status": "sent"}})

    return {"message": "WhatsApp alert sent", "alert_id": str(alert_result.inserted_id), "sent": sent}


@router.post("/log-call")
async def log_call(data: dict, user=Depends(get_current_user)):
    db = get_db()
    alert_id = data.get("alert_id")
    report_id = data.get("report_id")
    note = data.get("note", "Manual call logged")

    if alert_id:
        await db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {"status": "escalated", "contact_method": "call"}, "$inc": {"escalation_count": 1}},
        )

    return {"message": "Call logged"}


@router.post("/send-patient-alert")
async def send_patient_alert(data: SendAlertRequest, user=Depends(get_current_user)):
    db = get_db()
    report = await db.reports.find_one({"_id": ObjectId(data.report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    patient = await db.patients.find_one({"_id": report["patient_id"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not patient.get("doctor_whatsapp"):
        raise HTTPException(status_code=400, detail="No doctor assigned. Please add a doctor first.")

    vision_data = json.loads(report.get("nvidia_vision_raw", "{}"))
    critical_findings = vision_data.get("critical_findings", [])
    extracted_values = report.get("extracted_values", [])
    health_summary = report.get("health_summary", "")

    now = datetime.utcnow()
    time_str = now.strftime("%d %b %Y, %I:%M %p")

    critical_lines = ""
    if critical_findings:
        critical_lines = "\n".join(f"- {f}" for f in critical_findings)
    elif extracted_values:
        cv = [v for v in extracted_values if v.get("status", "").lower() == "critical"]
        if cv:
            critical_lines = "\n".join(
                f"- {v['test_name']}: {v.get('value', '')} {v.get('unit', '')} — Critically {v.get('status', 'Abnormal')}"
                for v in cv
            )
        else:
            critical_lines = "- Critical values detected in report"
    else:
        critical_lines = "- Critical values detected in report"

    header_val = f"{patient.get('age', '')}{patient.get('gender', '')[0]}" if patient.get('age') else patient.get('gender', '')

    msg = (
        f"🚨 CRITICAL ALERT — VitalAlert\n\n"
        f"Patient: {patient['name']}, {header_val}\n"
        f"Report: {report.get('report_type', 'Report')}\n"
        f"Time: {time_str}\n\n"
        f"⚠️ Critical Findings:\n{critical_lines}\n\n"
        f"Summary:\n{health_summary}\n\n"
        f"Action: Contact patient immediately.\n\n"
        f"Patient Phone: {patient.get('phone', 'N/A')}\n\n"
        f"— VitalAlert"
    )

    doctor_whatsapp = patient["doctor_whatsapp"]
    doctor_name = patient.get("doctor_name", "Doctor")

    whatsapp_result = await send_whatsapp(doctor_whatsapp, msg)
    sent = whatsapp_result["success"]

    if ALERT_CC_WHATSAPP:
        await send_whatsapp(ALERT_CC_WHATSAPP, msg)

    doctor_lookup = await db.doctors.find_one({"name": doctor_name}) if doctor_name != "Doctor" else None

    alert_doc = {
        "report_id": ObjectId(data.report_id),
        "patient_id": report["patient_id"],
        "doctor_id": doctor_lookup["_id"] if doctor_lookup else None,
        "doctor_name": doctor_name,
        "doctor_whatsapp": doctor_whatsapp,
        "alert_type": "patient_manual",
        "message_sent": msg,
        "status": "sent" if sent else "failed",
        "whatsapp_status": "sent" if sent else "failed",
        "contact_method": "whatsapp",
        "escalation_count": 0,
        "sent_at": now,
    }
    alert_result = await db.alerts.insert_one(alert_doc)

    await db.reports.update_one(
        {"_id": ObjectId(data.report_id)},
        {"$set": {"alert_status": "sent", "alert_sent": True, "alert_sent_to": doctor_name, "alert_sent_at": time_str}},
    )

    return {
        "message": "Alert sent to doctor" if sent else "Failed to send alert",
        "alert_id": str(alert_result.inserted_id),
        "sent": sent,
        "doctor_name": doctor_name,
    }
