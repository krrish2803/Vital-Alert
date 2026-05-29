import asyncio
import logging
from datetime import datetime, timedelta
from bson import ObjectId
from database import get_db
from services.whatsapp_service import send_whatsapp
from config import ESCALATION_MINUTES, FRONTEND_URL

logger = logging.getLogger(__name__)

ESCALATION_INTERVAL_SECONDS = 60
MAX_ESCALATIONS = 3


async def escalate_alerts():
    db = get_db()
    if db is None:
        return

    cutoff = datetime.utcnow() - timedelta(minutes=ESCALATION_MINUTES)

    cursor = db.alerts.find({
        "status": "sent",
        "sent_at": {"$lte": cutoff},
        "escalation_count": {"$lt": MAX_ESCALATIONS},
    })

    escalated = 0
    async for alert in cursor:
        try:
            await _escalate_single(db, alert)
            escalated += 1
        except Exception as e:
            logger.error(f"Escalation failed for alert {alert.get('_id')}: {e}")

    if escalated:
        logger.info(f"Escalated {escalated} alert(s)")


async def _escalate_single(db, alert):
    alert_id = alert["_id"]
    doctor_id = alert["doctor_id"]
    patient_id = alert["patient_id"]
    report_id = alert["report_id"]
    current_count = alert.get("escalation_count", 0)

    doctor = await db.doctors.find_one({"_id": doctor_id})
    if not doctor:
        logger.warning(f"Doctor {doctor_id} not found for escalation")
        return

    patient = await db.patients.find_one({"_id": patient_id})
    if not patient:
        logger.warning(f"Patient {patient_id} not found for escalation")

    report = await db.reports.find_one({"_id": report_id})

    target_number = doctor.get("backup_contact") or doctor["whatsapp_number"]
    target_label = "Backup contact" if doctor.get("backup_contact") else "Doctor"

    time_str = alert["sent_at"].strftime("%d %b %Y %I:%M %p")
    patient_name = patient["name"] if patient else "Unknown"
    report_type = report.get("report_type", "Report") if report else "Report"
    findings = ""
    if report:
        raw = report.get("nvidia_vision_raw", "{}")
        try:
            import json
            vd = json.loads(raw)
            findings = "\n".join(vd.get("critical_findings", []))
        except (json.JSONDecodeError, Exception):
            findings = "Critical values detected"
    findings = findings or "Critical values detected"

    step = current_count + 1
    msg = (
        f"🚨 ESCALATION ({step}/{MAX_ESCALATIONS}) — VitalAlert\n\n"
        f"Original alert sent {time_str} to Dr. {doctor['name']} was NOT acknowledged.\n\n"
        f"Patient: {patient_name}, {patient['age']}{patient['gender'][0] if patient else ''}\n"
        f"Report: {report_type}\n\n"
        f"⚠️ Critical Findings:\n{findings}\n\n"
        f"View: {FRONTEND_URL}/portal/{str(report_id)}\n\n"
        f"— VitalAlert Escalation System"
    )

    whatsapp_result = await send_whatsapp(target_number, msg)
    sent = whatsapp_result["success"]

    now = datetime.utcnow()
    await db.alerts.update_one(
        {"_id": alert_id},
        {
            "$set": {
                "status": "escalated" if sent else "sent",
                "escalated_at": now,
                "escalation_target": target_label,
                "escalation_message": msg,
            },
            "$inc": {"escalation_count": 1},
        },
    )

    log = (
        f"Escalation {step}/{MAX_ESCALATIONS}: sent to {target_label} "
        f"({target_number}) — {'✓' if sent else '✗'}"
    )
    logger.info(f"Alert {alert_id}: {log}")


async def run_escalation_loop():
    logger.info(
        f"Escalation service started (check every {ESCALATION_INTERVAL_SECONDS}s, "
        f"threshold={ESCALATION_MINUTES}m, max={MAX_ESCALATIONS}x)"
    )
    while True:
        try:
            await escalate_alerts()
        except Exception as e:
            logger.error(f"Escalation loop error: {e}")
        await asyncio.sleep(ESCALATION_INTERVAL_SECONDS)
