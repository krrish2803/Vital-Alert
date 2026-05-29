import os
import json
import base64
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse
from database import get_db
from auth import get_current_user
from services.nvidia_vision_service import extract_report_data
from services.nvidia_language_service import generate_health_summary
from services.pdf_service import pdf_to_base64_images
from services.alert_service import process_analysis
from PIL import Image
from io import BytesIO
from bson import ObjectId
from config import UPLOAD_DIR, MAX_FILE_SIZE_MB, MAX_FILES_PER_UPLOAD, JWT_SECRET
import jwt

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


@router.post("/upload")
async def upload_report(
    patient_id: str = Form(...),
    report_type: str = Form(...),
    notes: str = Form(""),
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    db = get_db()

    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail=f"Max {MAX_FILES_PER_UPLOAD} files allowed")
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="At least 1 file required")

    patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    saved_files = []
    all_images_base64 = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {ext} not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds {MAX_FILE_SIZE_MB}MB")

        file_id = f"{patient_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        safe_name = f"{file_id}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        if ext == ".pdf":
            images = pdf_to_base64_images(file_path)
            all_images_base64.extend(images)
            page_count = len(images)
            saved_files.append({
                "filename": file.filename,
                "file_path": file_path,
                "file_type": "pdf",
                "page_count": page_count,
                "file_size": len(content),
            })
        else:
            try:
                img = Image.open(BytesIO(content))
                img.verify()
                buffered = BytesIO()
                img = Image.open(BytesIO(content))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(buffered, format="JPEG", quality=85)
                b64 = base64.b64encode(buffered.getvalue()).decode()
                all_images_base64.append(b64)
                saved_files.append({
                    "filename": file.filename,
                    "file_path": file_path,
                    "file_type": "image",
                    "page_count": 1,
                    "file_size": len(content),
                })
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid image file: {file.filename}")

    vision_result = await extract_report_data(all_images_base64, report_type)

    health_summary = ""
    has_values = bool(vision_result.get("extracted_values"))
    has_findings = bool(vision_result.get("critical_findings"))
    if has_values or has_findings:
        health_summary = await generate_health_summary(
            vision_result,
            {"name": patient["name"], "age": patient["age"], "gender": patient["gender"]},
            report_type,
        )

    report_doc = {
        "patient_id": ObjectId(patient_id),
        "report_type": report_type,
        "files": saved_files,
        "nvidia_vision_raw": json.dumps(vision_result),
        "extracted_values": vision_result.get("extracted_values", []),
        "health_summary": health_summary,
        "impression": vision_result.get("impression", ""),
        "critical_findings": vision_result.get("critical_findings", []),
        "is_critical": vision_result.get("is_critical", False),
        "confidence_score": vision_result.get("confidence_score", 0.0),
        "severity": vision_result.get("severity", "normal"),
        "requires_human_review": vision_result.get("is_critical", False) and vision_result.get("confidence_score", 1) < 0.75,
        "suggested_action": vision_result.get("suggested_action", ""),
        "alert_status": "pending",
        "notes": notes,
        "uploaded_by": ObjectId(user["id"]),
        "uploaded_at": datetime.utcnow(),
        "processed_at": datetime.utcnow(),
    }

    result = await db.reports.insert_one(report_doc)
    report_id = str(result.inserted_id)

    await db.patients.update_one(
        {"_id": ObjectId(patient_id)},
        {"$inc": {"total_visits": 1}, "$set": {"last_visit": datetime.utcnow()}},
    )

    alert_result = await process_analysis(report_id, patient_id, vision_result)

    report_doc["id"] = report_id

    is_critical = vision_result.get("is_critical", False)
    confidence = vision_result.get("confidence_score", 0.0)
    alert_sent = alert_result.get("status") == "sent" if alert_result else False
    requires_review = is_critical and confidence < 0.75

    resp = {
        "id": report_id,
        "patient_id": patient_id,
        "report_type": report_type,
        "extracted_values": vision_result.get("extracted_values", []),
        "health_summary": health_summary,
        "impression": vision_result.get("impression", ""),
        "critical_findings": vision_result.get("critical_findings", []),
        "is_critical": is_critical,
        "confidence_score": confidence,
        "severity": vision_result.get("severity", "normal"),
        "requires_human_review": requires_review,
        "suggested_action": vision_result.get("suggested_action", ""),
        "alert_status": alert_result.get("status", "none") if alert_result else "none",
    }

    no_doctor = alert_result and alert_result.get("status") == "no_doctor"

    msg = "Report analyzed successfully"
    if alert_sent:
        resp["alert_sent"] = True
        resp["alert_sent_to"] = alert_result.get("doctor_name", "Doctor")
        resp["alert_sent_at"] = alert_result.get("sent_at", "")
        msg = "Critical report detected. Doctor alerted on WhatsApp."
    elif no_doctor:
        resp["alert_sent"] = False
        msg = "Critical report detected — Please add your doctor's contact to receive the alert."
    elif requires_review:
        resp["alert_sent"] = False
        msg = "Critical report detected — confidence too low for auto-alert. Flagged for manual review."
    else:
        resp["alert_sent"] = False

    return {"message": msg, "report": resp}


@router.get("")
async def get_reports(
    page: int = 1, limit: int = 20,
    patient_id: str = None,
    report_type: str = None,
    user=Depends(get_current_user),
):
    db = get_db()
    query = {}
    if patient_id:
        query["patient_id"] = ObjectId(patient_id)
    if report_type:
        query["report_type"] = report_type
    skip = (page - 1) * limit
    cursor = db.reports.find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
    reports = await cursor.to_list(length=limit)
    total = await db.reports.count_documents(query)
    return {
        "reports": [{"id": str(r.pop("_id")), **r} for r in reports],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/critical")
async def get_critical_reports(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.reports.find({"is_critical": True}).sort("uploaded_at", -1).limit(50)
    reports = await cursor.to_list(length=50)
    return {"reports": [{"id": str(r.pop("_id")), **r} for r in reports]}


@router.get("/{report_id}/download/{file_index}")
async def download_report_file(report_id: str, file_index: int = 0, token: str = Query(None), credentials=Depends(HTTPBearer(auto_error=False))):
    if credentials:
        try:
            jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    elif token:
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    files = report.get("files", [])
    if file_index < 0 or file_index >= len(files):
        raise HTTPException(status_code=404, detail="File not found")
    file_info = files[file_index]
    file_path = file_info.get("file_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    original_name = file_info.get("filename", f"report_{report_id}.pdf")
    return FileResponse(file_path, filename=original_name, media_type="application/octet-stream")


@router.get("/{report_id}")
async def get_report(report_id: str, user=Depends(get_current_user)):
    db = get_db()
    report = await db.reports.find_one({"_id": ObjectId(report_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    patient = await db.patients.find_one({"_id": report["patient_id"]})
    report["id"] = str(report["_id"])
    return {
        "report": report,
        "patient": {"id": str(patient.pop("_id")), **patient} if patient else None,
    }
