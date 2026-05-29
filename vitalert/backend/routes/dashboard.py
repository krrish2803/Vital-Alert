from fastapi import APIRouter, Depends
from database import get_db
from auth import get_current_user
from bson import ObjectId
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# Only count reports that went through AI analysis (have extracted values)
_REAL_REPORT_FILTER = {"extracted_values": {"$exists": True, "$ne": []}}


@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    db = get_db()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    today_reports = await db.reports.count_documents({
        **{"uploaded_at": {"$gte": today_start}},
        **_REAL_REPORT_FILTER,
    })
    yesterday_reports = await db.reports.count_documents({
        **{"uploaded_at": {"$gte": yesterday_start, "$lt": today_start}},
        **_REAL_REPORT_FILTER,
    })

    critical_alerts = await db.alerts.count_documents({"status": "sent"})
    resolved_alerts = await db.alerts.count_documents({"status": "resolved"})
    pending_alerts = await db.alerts.count_documents({"status": {"$in": ["sent", "pending"]}})
    acknowledged_alerts = await db.alerts.count_documents({"status": "acknowledged"})

    return {
        "total_reports_today": today_reports,
        "reports_vs_yesterday": today_reports - yesterday_reports,
        "critical_alerts": critical_alerts,
        "critical_alerts_vs_yesterday": await _count_alerts_since(db, yesterday_start, today_start),
        "resolved_alerts": resolved_alerts,
        "resolution_rate": round((resolved_alerts / max(critical_alerts + resolved_alerts + acknowledged_alerts + pending_alerts, 1)) * 100),
        "pending_alerts": pending_alerts,
    }


@router.get("/reports-by-type")
async def get_reports_by_type(user=Depends(get_current_user)):
    db = get_db()
    week_start = datetime.utcnow() - timedelta(days=7)
    pipeline = [
        {"$match": {"uploaded_at": {"$gte": week_start}, "extracted_values": {"$exists": True, "$ne": []}}},
        {"$group": {"_id": "$report_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cursor = db.reports.aggregate(pipeline)
    results = await cursor.to_list(length=20)
    return {"report_types": [{"type": r["_id"], "count": r["count"]} for r in results]}


@router.get("/alerts-by-day")
async def get_alerts_by_day(user=Depends(get_current_user)):
    db = get_db()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    days = []
    for i in range(6, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = await db.alerts.count_documents({"sent_at": {"$gte": day_start, "$lt": day_end}})
        days.append({"date": day_start.strftime("%a"), "count": count})
    return {"alerts_by_day": days}


@router.get("/top-doctors")
async def get_top_doctors(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.doctors.find().sort("total_referrals", -1).limit(5)
    doctors = await cursor.to_list(length=5)
    return {"doctors": [{"id": str(d.pop("_id")), **d} for d in doctors]}


@router.get("/recent-alerts")
async def get_recent_alerts(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.alerts.find().sort("sent_at", -1).limit(10)
    alerts = await cursor.to_list(length=10)
    enriched = []
    for alert in alerts:
        alert["id"] = str(alert["_id"])
        patient = await db.patients.find_one({"_id": alert["patient_id"]})
        doctor = await db.doctors.find_one({"_id": alert["doctor_id"]})
        report = await db.reports.find_one({"_id": alert["report_id"]})
        if patient:
            alert["patient_name"] = patient.get("name")
            alert["patient_age"] = patient.get("age")
            alert["patient_gender"] = patient.get("gender")
        if doctor:
            alert["doctor_name"] = doctor.get("name")
        if report:
            alert["report_type"] = report.get("report_type")
            values = report.get("extracted_values", [])
            if values:
                critical_val = next((v for v in values if "critical" in v.get("status", "")), None)
                alert["critical_value"] = f"{critical_val['test_name']} {critical_val['value']}" if critical_val else ""
        enriched.append(alert)
    return {"alerts": enriched}


@router.get("/recent-patients")
async def get_recent_patients(user=Depends(get_current_user)):
    db = get_db()
    pipeline = [
        {"$match": {"extracted_values": {"$exists": True, "$ne": []}}},
        {"$sort": {"uploaded_at": -1}},
        {"$limit": 10},
        {"$group": {
            "_id": "$patient_id",
            "report_type": {"$first": "$report_type"},
            "is_critical": {"$first": "$is_critical"},
            "uploaded_at": {"$first": "$uploaded_at"},
        }},
        {"$sort": {"uploaded_at": -1}},
    ]
    cursor = db.reports.aggregate(pipeline)
    entries = await cursor.to_list(length=10)
    enriched = []
    for entry in entries:
        patient = await db.patients.find_one({"_id": entry["_id"]})
        if patient:
            enriched.append({
                "patient_id": str(entry["_id"]),
                "name": patient.get("name"),
                "age": patient.get("age"),
                "gender": patient.get("gender"),
                "report_type": entry.get("report_type"),
                "is_critical": entry.get("is_critical", False),
                "uploaded_at": entry.get("uploaded_at"),
            })
    return {"patients": enriched}


async def _count_alerts_since(db, start, end):
    return await db.alerts.count_documents({"sent_at": {"$gte": start, "$lt": end}})
