from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.db.mongodb import get_database

router = APIRouter()


class AuthPayload(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=256)


class AuthUser(BaseModel):
    id: str
    username: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


def _hash_password(password: str) -> str:
    # Lightweight hash for this project flow; replace with bcrypt in production.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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
        access_token=secrets.token_urlsafe(32),
        user=AuthUser(id=str(res.inserted_id), username=username),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthPayload):
    users = _users_collection()
    username = payload.username.strip()
    user = await users.find_one({"username": username})

    if not user or user.get("password_hash") != _hash_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return AuthResponse(
        access_token=secrets.token_urlsafe(32),
        user=AuthUser(id=str(user["_id"]), username=username),
    )
