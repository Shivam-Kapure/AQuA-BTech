from __future__ import annotations

from datetime import datetime
import hashlib
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

    async def ensure_indexes(self) -> None:
        await self.collection.create_index([("owner_id", 1), ("project_name", 1), ("created_at", -1)])
        await self.collection.create_index([("owner_id", 1), ("project_name", 1), ("operation_id", 1), ("category", 1)])
        await self.collection.create_index([("owner_id", 1), ("project_name", 1), ("fingerprint", 1)], unique=True, sparse=True)

    async def create_many(self, findings: list[ApiFindingRecord]) -> list[ApiFindingRecord]:
        if not findings:
            return []
        saved: list[ApiFindingRecord] = []
        for finding in findings:
            doc = finding.model_dump(exclude={"id"})
            fingerprint_payload = "|".join((finding.operation_id or "", finding.category, finding.finding))
            doc["fingerprint"] = finding.fingerprint or hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
            now = datetime.utcnow()
            doc.update({"created_at": now, "first_seen_at": now, "last_seen_at": now, "occurrences": 1})
            await self.collection.update_one(
                {"owner_id": finding.owner_id, "project_name": finding.project_name, "fingerprint": doc["fingerprint"]},
                {
                    "$set": {key: value for key, value in doc.items() if key not in {"created_at", "first_seen_at", "occurrences"}},
                    "$setOnInsert": {"created_at": now, "first_seen_at": now, "occurrences": 0},
                    "$inc": {"occurrences": 1},
                },
                upsert=True,
            )
            stored = await self.collection.find_one({"owner_id": finding.owner_id, "project_name": finding.project_name, "fingerprint": doc["fingerprint"]})
            if stored:
                if isinstance(stored.get("_id"), ObjectId):
                    stored["id"] = str(stored.pop("_id"))
                saved.append(ApiFindingRecord.model_validate(stored))
        return saved

    async def list(self, *, owner_id: str, project_name: str | None = None) -> list[ApiFindingRecord]:
        query: dict[str, Any] = {"owner_id": owner_id}
        if project_name is not None:
            query["project_name"] = project_name
        docs = await self.collection.find(query).sort("created_at", -1).limit(500).to_list(length=500)
        for doc in docs:
            if isinstance(doc.get("_id"), ObjectId):
                doc["id"] = str(doc.pop("_id"))
        return [ApiFindingRecord.model_validate(doc) for doc in docs]

    async def update_remediation(
        self,
        finding_id: str,
        *,
        owner_id: str,
        remediation_status: str,
        remediation_note: str | None,
    ) -> ApiFindingRecord | None:
        try:
            object_id = ObjectId(finding_id)
        except Exception:
            return None
        await self.collection.update_one(
            {"_id": object_id, "owner_id": owner_id},
            {"$set": {"remediation_status": remediation_status, "remediation_note": remediation_note}},
        )
        doc = await self.collection.find_one({"_id": object_id, "owner_id": owner_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return ApiFindingRecord.model_validate(doc)
