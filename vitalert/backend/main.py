import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import connect_db, close_db
from routes import auth, patients, reports, doctors, alerts, dashboard, reviews
from services.changestream_service import watch_reports_collection
from services.escalation_service import run_escalation_loop
from bson import ObjectId
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

background_tasks = set()


class VitalertJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def patch_jsonable_encoder():
    """Monkey-patch FastAPI's jsonable_encoder to handle ObjectId."""
    from fastapi import encoders as fastapi_encoders
    original = fastapi_encoders.jsonable_encoder

    def patched(obj, *args, **kwargs):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {k: patched(v, *args, **kwargs) for k, v in obj.items()}
        if isinstance(obj, list):
            return [patched(v, *args, **kwargs) for v in obj]
        if isinstance(obj, tuple):
            return tuple(patched(v, *args, **kwargs) for v in obj)
        return original(obj, *args, **kwargs)

    fastapi_encoders.jsonable_encoder = patched


patch_jsonable_encoder()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VitalAlert backend...")
    await connect_db()
    is_vercel = os.environ.get("VERCEL", "")
    if not is_vercel:
        task = asyncio.create_task(watch_reports_collection())
        background_tasks.add(task)
        esc_task = asyncio.create_task(run_escalation_loop())
        background_tasks.add(esc_task)
    yield
    if not is_vercel:
        task.cancel()
        esc_task.cancel()
    await close_db()
    logger.info("VitalAlert backend stopped.")


app = FastAPI(
    title="VitalAlert API",
    description="AI-powered diagnostic report analysis and critical alert system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(reports.router)
app.include_router(doctors.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(reviews.router)


@app.get("/")
async def root():
    return {"message": "VitalAlert API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
