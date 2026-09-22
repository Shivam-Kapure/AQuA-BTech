from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from app.db.mongodb import get_database
from app.models.common import to_object_id
from app.models.security_test import SecurityTestCaseCreate, SecurityTestCaseInDB


class SecurityTestCaseRepository:
    def __init__(self, project_name: str):
        if not project_name:
            raise ValueError("project_name is required to resolve security test cases collection")
        safe_name = "".join([c if c.isalnum() else "_" for c in project_name])
        self.collection_name = f"security_tests_{safe_name}"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        """Enforce logical security-test IDs within this legacy project collection."""
        await self.collection.create_index([("project_id", 1), ("test_id", 1)], unique=True, sparse=True)
        await self.collection.create_index([("project_id", 1), ("created_at", -1)])

    async def create_many(
        self,
        test_cases: list[SecurityTestCaseCreate],
        *,
        project_id: str | ObjectId | None = None,
    ) -> list[SecurityTestCaseInDB]:
        if not test_cases:
            return []
        await self.ensure_indexes()
        now = datetime.utcnow()
        docs: list[dict[str, Any]] = []
        for tc in test_cases:
            doc: dict[str, Any] = tc.model_dump()
            if project_id is not None:
                doc["project_id"] = to_object_id(project_id)
            doc["created_at"] = now
            doc["updated_at"] = now
            doc["status"] = "draft"
            docs.append(doc)

        res = await self.collection.insert_many(docs)
        for doc, _id in zip(docs, res.inserted_ids, strict=False):
            doc["_id"] = str(_id)
            if "project_id" in doc and isinstance(doc["project_id"], ObjectId):
                doc["project_id"] = str(doc["project_id"])
        return [SecurityTestCaseInDB.model_validate(doc) for doc in docs]

    async def list(
        self,
        *,
        project_id: str | ObjectId | None = None,
        url: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[SecurityTestCaseInDB]:
        query: dict[str, Any] = {}
        if project_id is not None:
            query["project_id"] = to_object_id(project_id)
        if url is not None:
            query["url"] = url

        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(max(skip, 0))
            .limit(min(max(limit, 1), 500))
        )
        docs = await cursor.to_list(length=None)
        for doc in docs:
            if "_id" in doc and isinstance(doc["_id"], ObjectId):
                doc["_id"] = str(doc["_id"])
            if "project_id" in doc and isinstance(doc["project_id"], ObjectId):
                doc["project_id"] = str(doc["project_id"])
        return [SecurityTestCaseInDB.model_validate(doc) for doc in docs]

    async def get_by_project_and_test_id(
        self,
        *,
        project_id: str | ObjectId,
        test_id: str,
    ) -> SecurityTestCaseInDB | None:
        pid = to_object_id(project_id)

        query: dict[str, Any] = {"project_id": pid}
        ors: list[dict[str, Any]] = [{"test_id": test_id}]

        try:
            ors.append({"_id": to_object_id(test_id)})
        except Exception:
            pass

        query["$or"] = ors
        doc = await self.collection.find_one(query)
        if not doc:
            return None
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        if "project_id" in doc and isinstance(doc.get("project_id"), ObjectId):
            doc["project_id"] = str(doc["project_id"])
        return SecurityTestCaseInDB.model_validate(doc)

    async def update_status(
        self,
        test_case_id: str | ObjectId,
        *,
        status: str,
        failure_reason: str | None = None,
        finding: str | None = None,
        evidence: str | None = None,
        recommendation: str | None = None,
    ) -> None:
        now = datetime.utcnow()
        await self.collection.update_one(
            {"_id": to_object_id(test_case_id)},
            {
                "$set": {
                    "status": status,
                    "failure_reason": failure_reason,
                    "finding": finding,
                    "evidence": evidence,
                    "recommendation": recommendation,
                    "updated_at": now,
                }
            },
        )
