from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from app.db.mongodb import get_database
from app.models.api_spec import ApiRunRecord


class ApiRunRepository:
    collection_name = "api_runs"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def create(self, run: ApiRunRecord) -> ApiRunRecord:
        doc: dict[str, Any] = run.model_dump(exclude={"id"})
        doc["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return ApiRunRecord.model_validate(doc)

    async def list(self, *, owner_id: str, project_name: str | None = None) -> list[ApiRunRecord]:
        query: dict[str, Any] = {"owner_id": owner_id}
        if project_name is not None:
            query["project_name"] = project_name
        docs = await self.collection.find(query).sort("created_at", -1).limit(500).to_list(length=500)
        for doc in docs:
            if isinstance(doc.get("_id"), ObjectId):
                doc["id"] = str(doc.pop("_id"))
        return [ApiRunRecord.model_validate(doc) for doc in docs]

    async def get(self, run_id: str, *, owner_id: str) -> ApiRunRecord | None:
        try:
            object_id = ObjectId(run_id)
        except Exception:
            return None
        doc = await self.collection.find_one({"_id": object_id, "owner_id": owner_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return ApiRunRecord.model_validate(doc)
