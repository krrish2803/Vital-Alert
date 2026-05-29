from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import hash_password, verify_password, create_token, get_current_user
from models.user import UserCreate, UserLogin
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel

class RoleUpdate(BaseModel):
    role: str

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register")
async def register(data: UserCreate):
    db = get_db()
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "name": data.name,
        "email": data.email,
        "password": hash_password(data.password),
        "role": data.role,
        "clinic_name": data.clinic_name,
        "created_at": datetime.utcnow(),
    }
    result = await db.users.insert_one(user)
    token = create_token({"id": str(result.inserted_id), "email": data.email, "role": data.role})
    return {
        "token": token,
        "user": {
            "id": str(result.inserted_id),
            "name": data.name,
            "email": data.email,
            "role": data.role,
            "clinic_name": data.clinic_name,
            "created_at": datetime.utcnow().isoformat(),
        },
        "role": data.role,
    }


@router.patch("/role")
async def update_role(data: RoleUpdate, user=Depends(get_current_user)):
    db = get_db()
    if data.role not in ("owner", "staff", "doctor", "patient"):
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"role": data.role}})
    token = create_token({"id": user["id"], "email": user["email"], "role": data.role})
    return {"token": token, "role": data.role, "message": f"Role updated to {data.role}"}


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    db = get_db()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(u["_id"]),
        "name": u["name"],
        "email": u["email"],
        "role": u["role"],
        "clinic_name": u.get("clinic_name"),
    }


@router.post("/login")
async def login(data: UserLogin):
    db = get_db()
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token({"id": str(user["_id"]), "email": user["email"], "role": user["role"]})
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "clinic_name": user.get("clinic_name"),
        },
        "role": user["role"],
    }
