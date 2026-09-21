from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from app.db.mongodb import get_database
from app.models.api_spec import ApiFindingRecord


class ApiFindingRepository:
    collection_name = "api_findings"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def create_many(self, findings: list[ApiFindingRecord]) -> list[ApiFindingRecord]:
        if not findings:
            return []
        docs: list[dict[str, Any]] = []
        for finding in findings:
            doc = finding.model_dump(exclude={"id"})
            doc["created_at"] = datetime.utcnow()
            docs.append(doc)
        result = await self.collection.insert_many(docs)
        for doc, object_id in zip(docs, result.inserted_ids, strict=False):
            doc["id"] = str(object_id)
        return [ApiFindingRecord.model_validate(doc) for doc in docs]

    async def list(self, *, owner_id: str, project_name: str | None = None) -> list[ApiFindingRecord]:
        query: dict[str, Any] = {"owner_id": owner_id}
        if project_name is not None:
            query["project_name"] = project_name
        docs = await self.collection.find(query).sort("created_at", -1).limit(500).to_list(length=500)
        for doc in docs:
            if isinstance(doc.get("_id"), ObjectId):
                doc["id"] = str(doc.pop("_id"))
        return [ApiFindingRecord.model_validate(doc) for doc in docs]
