from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from app.db.mongodb import get_database
from app.models.common import to_object_id
from app.models.project import ProjectCreate, ProjectInDB


class ProjectRepository:
    collection_name = "projects"

    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB is not connected")
        return db[self.collection_name]

    async def create_one(self, project: ProjectCreate) -> ProjectInDB:
        now = datetime.utcnow()
        doc: dict[str, Any] = project.model_dump()
        doc["created_at"] = now
        doc["updated_at"] = now
        res = await self.collection.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        return ProjectInDB.model_validate(doc)

    async def get_by_id(self, project_id: str | ObjectId) -> ProjectInDB | None:
        query = {"_id": to_object_id(project_id)}
        doc = await self.collection.find_one(query)
        if not doc:
            return None
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        return ProjectInDB.model_validate(doc)

    async def get_by_name(self, name: str) -> ProjectInDB | None:
        doc = await self.collection.find_one({"name": name})
        if not doc:
            return None
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        return ProjectInDB.model_validate(doc)

    async def get_or_create_by_name(
        self,
        name: str,
        *,
        description: str | None = None,
        url: str | None = None,
    ) -> ProjectInDB:
        existing = await self.get_by_name(name)
        if existing:
            # Optionally update URL if provided and not present
            if url and not existing.url:
                await self.collection.update_one(
                    {"_id": to_object_id(existing.id)},
                    {"$set": {"url": url}}
                )
                existing.url = url
            return existing
        project = ProjectCreate(name=name, description=description, url=url)
        return await self.create_one(project)

    async def list(self) -> list[ProjectInDB]:
        cursor = self.collection.find().sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        for doc in docs:
            if "_id" in doc and isinstance(doc["_id"], ObjectId):
                doc["_id"] = str(doc["_id"])
        return [ProjectInDB.model_validate(doc) for doc in docs]

