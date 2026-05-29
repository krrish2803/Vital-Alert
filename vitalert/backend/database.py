from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, MONGODB_DB_NAME

client = None
db = None


async def connect_db():
    global client, db
    if client is None:
        client = AsyncIOMotorClient(MONGODB_URI, maxPoolSize=10)
        db = client[MONGODB_DB_NAME]
        existing = await db.list_collection_names()
        if "users" not in existing:
            await db.users.create_index("email", unique=True)
            await db.patients.create_index("phone")
            await db.patients.create_index("referring_doctor_id")
            await db.reports.create_index("patient_id")
            await db.reports.create_index([("uploaded_at", -1)])
            await db.alerts.create_index("report_id")
            await db.alerts.create_index("doctor_id")
            await db.alerts.create_index([("status", 1), ("sent_at", 1)])
    return db


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return db
