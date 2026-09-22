from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.db.mongodb import get_database
from app.models.test_run import TestRunRecord

__test__ = False


class TestRunRepository:
    collection_name = "test_runs"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index([("owner_id", 1), ("project_id", 1), ("created_at", -1)])
        await self.collection.create_index([("owner_id", 1), ("correlation_id", 1)], unique=True, sparse=True)

    async def create(self, run: TestRunRecord) -> TestRunRecord:
        doc: dict[str, Any] = run.model_dump(exclude={"id"}, mode="json")
        result = await self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return TestRunRecord.model_validate(doc)

    async def list(self, *, owner_id: str, project_id: str | None = None, project_name: str | None = None) -> list[TestRunRecord]:
        query: dict[str, Any] = {"owner_id": owner_id}
        if project_id is not None:
            query["project_id"] = project_id
        if project_name is not None:
            query["project_name"] = project_name
        docs = await self.collection.find(query).sort("created_at", -1).limit(500).to_list(length=500)
        for doc in docs:
            if isinstance(doc.get("_id"), ObjectId):
                doc["id"] = str(doc.pop("_id"))
        return [TestRunRecord.model_validate(doc) for doc in docs]

    async def get(self, run_id: str, *, owner_id: str) -> TestRunRecord | None:
        if not ObjectId.is_valid(run_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(run_id), "owner_id": owner_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return TestRunRecord.model_validate(doc)
