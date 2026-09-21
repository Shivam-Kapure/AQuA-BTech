from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from app.db.mongodb import get_database
from app.models.api_spec import ApiSpecRecord


class ApiSpecRepository:
    collection_name = "api_specs"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def create(self, spec: ApiSpecRecord) -> ApiSpecRecord:
        doc: dict[str, Any] = spec.model_dump(exclude={"id"})
        doc["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        doc["id"] = doc.pop("_id")
        return ApiSpecRecord.model_validate(doc)

    async def next_version(self, *, owner_id: str, project_name: str | None, checksum: str | None = None) -> int:
        query = {"owner_id": owner_id, "project_name": project_name}
        existing = await self.collection.count_documents(query)
        return int(existing) + 1

    async def list(self, *, owner_id: str, project_name: str | None = None) -> list[ApiSpecRecord]:
        query: dict[str, Any] = {"owner_id": owner_id}
        if project_name is not None:
            query["project_name"] = project_name
        docs = await self.collection.find(query).sort("created_at", -1).to_list(length=500)
        for doc in docs:
            if isinstance(doc.get("_id"), ObjectId):
                doc["id"] = str(doc.pop("_id"))
        return [ApiSpecRecord.model_validate(doc) for doc in docs]
