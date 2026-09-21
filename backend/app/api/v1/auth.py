from __future__ import annotations

from datetime import datetime

import bcrypt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.db.mongodb import get_database
from app.core.auth import create_access_token

router = APIRouter()


class AuthPayload(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    # bcrypt only accepts passwords up to 72 bytes; reject longer values rather
    # than silently truncating credentials before hashing.
    password: str = Field(min_length=6, max_length=72)


class AuthUser(BaseModel):
    id: str
    username: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


def _users_collection():
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not connected",
        )
    return db["users"]


@router.post("/register", response_model=AuthResponse)
async def register(payload: AuthPayload):
    users = _users_collection()
    username = payload.username.strip()

    existing = await users.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    now = datetime.utcnow()
    doc = {
        "username": username,
        "password_hash": _hash_password(payload.password),
        "created_at": now,
        "updated_at": now,
    }
    res = await users.insert_one(doc)

    return AuthResponse(
        access_token=create_access_token(user_id=str(res.inserted_id), username=username),
        user=AuthUser(id=str(res.inserted_id), username=username),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthPayload):
    users = _users_collection()
    username = payload.username.strip()
    user = await users.find_one({"username": username})

    if not user or not _verify_password(payload.password, str(user.get("password_hash", ""))):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return AuthResponse(
        access_token=create_access_token(user_id=str(user["_id"]), username=username),
        user=AuthUser(id=str(user["_id"]), username=username),
    )
