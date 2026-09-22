from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId

from app.config import settings
from app.db.mongodb import get_database
from app.models.test_run import ArtifactMetadata


class ArtifactRepository:
    collection_name = "artifacts"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index([("owner_id", 1), ("run_id", 1), ("created_at", -1)])
        await self.collection.create_index("expires_at", expireAfterSeconds=0)

    async def create(self, artifact: ArtifactMetadata) -> ArtifactMetadata:
        if artifact.byte_size is not None and artifact.byte_size > settings.ARTIFACT_MAX_BYTES:
            raise ValueError("Artifact exceeds the configured size limit")
        doc: dict[str, Any] = artifact.model_dump(exclude={"id"}, mode="json")
        result = await self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return ArtifactMetadata.model_validate(doc)

    async def list_for_run(self, run_id: str, *, owner_id: str) -> list[ArtifactMetadata]:
        query: dict[str, Any] = {"run_id": run_id, "owner_id": owner_id}
        docs = await self.collection.find(query).sort("created_at", -1).limit(500).to_list(length=500)
        for doc in docs:
            if isinstance(doc.get("_id"), ObjectId):
                doc["id"] = str(doc.pop("_id"))
        return [ArtifactMetadata.model_validate(doc) for doc in docs]

    async def delete_expired(self, *, now: datetime | None = None) -> int:
        cutoff = now or datetime.utcnow()
        result = await self.collection.delete_many({"expires_at": {"$lte": cutoff}})
        return int(result.deleted_count)


def default_artifact_expiry(*, created_at: datetime | None = None) -> datetime:
    return (created_at or datetime.utcnow()) + timedelta(days=settings.ARTIFACT_RETENTION_DAYS)
