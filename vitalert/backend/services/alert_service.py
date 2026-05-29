import json
import logging
from datetime import datetime
from bson import ObjectId
from database import get_db
from services.whatsapp_service import send_whatsapp
from config import FRONTEND_URL, ALERT_CC_WHATSAPP

logger = logging.getLogger(__name__)


async def process_analysis(report_id: str, patient_id: str, analysis: dict) -> dict:
    db = get_db()
    is_critical = analysis.get("is_critical", False)
    confidence = analysis.get("confidence_score", 0.0)

    if not is_critical:
        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"alert_status": "none"}},
        )
        return {"status": "none", "alert_id": None}

    patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    if not patient:
        logger.error(f"Patient {patient_id} not found for report {report_id}")
        return {"status": "error", "alert_id": None}

    # Determine doctor info: first check referring_doctor_id, then patient-assigned doctor
    doctor_id = patient.get("referring_doctor_id")
    doctor_whatsapp = None
    doctor_name = "Doctor"
    doctor_obj = None

    if doctor_id:
        doctor_obj = await db.doctors.find_one({"_id": doctor_id})
        if doctor_obj:
            doctor_whatsapp = doctor_obj.get("whatsapp_number")
            doctor_name = doctor_obj.get("name", "Doctor")

    # Fallback to patient-assigned doctor if no referring doctor
    if not doctor_whatsapp and patient.get("doctor_whatsapp"):
        doctor_whatsapp = patient["doctor_whatsapp"]
        doctor_name = patient.get("doctor_name", "Your Doctor")
        doctor_id = None
        if doctor_name and doctor_name != "Your Doctor":
            doctor_obj = await db.doctors.find_one({"name": doctor_name})

    if not doctor_whatsapp:
        logger.warning(f"No doctor contact for patient {patient_id}")
        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"alert_status": "no_doctor"}},
        )
        return {"status": "no_doctor", "alert_id": None}

    if confidence >= 0.75:
        now = datetime.utcnow()
        time_str = now.strftime("%I:%M:%S %p")
        critical_findings_text = "\n".join(analysis.get("critical_findings", [])) or "Critical values detected"
        health_summary = analysis.get("health_summary", "")
        suggested_action = analysis.get("suggested_action", "")

        msg = (
            f"🚨 CRITICAL ALERT — VitalAlert\n\n"
            f"Patient: {patient['name']}, {patient['age']}{patient['gender'][0]}\n"
            f"Report: {analysis.get('report_type', 'Report')}\n"
            f"Time: {time_str}\n\n"
            f"⚠️ Critical Findings:\n{critical_findings_text}\n\n"
            f"AI Summary:\n{health_summary}\n\n"
            f"Suggested Action:\n{suggested_action}\n\n"
            f"— VitalAlert System"
        )

        whatsapp_result = await send_whatsapp(doctor_whatsapp, msg)
        sent = whatsapp_result["success"]
        whatsapp_sid = whatsapp_result["sid"]

        if ALERT_CC_WHATSAPP:
            await send_whatsapp(ALERT_CC_WHATSAPP, msg)

        alert_doc = {
            "report_id": ObjectId(report_id),
            "patient_id": ObjectId(patient_id),
            "doctor_id": doctor_obj["_id"] if doctor_obj else None,
            "alert_type": "auto",
            "message_sent": msg,
            "status": "sent" if sent else "failed",
            "whatsapp_status": "sent" if sent else "failed",
            "whatsapp_sid": whatsapp_sid,
            "contact_method": "whatsapp",
            "escalation_count": 0,
            "sent_at": now,
        }
        alert_result = await db.alerts.insert_one(alert_doc)

        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"alert_status": "sent" if sent else "failed"}},
        )

        logger.info(f"Auto alert {'sent' if sent else 'failed'} for report {report_id}")
        return {
            "status": "sent" if sent else "failed",
            "alert_id": str(alert_result.inserted_id),
            "doctor_name": doctor_name,
            "sent_at": time_str,
            "whatsapp_sid": whatsapp_sid,
        }
    else:
        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {
                "$set": {
                    "requires_human_review": True,
                    "alert_status": "manual_review",
                }
            },
        )
        logger.info(f"Report {report_id} requires human review (confidence: {confidence})")
        return {"status": "manual_review", "alert_id": None}
