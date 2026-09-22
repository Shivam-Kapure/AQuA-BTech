from __future__ import annotations

import pytest

import app.db.repositories.project_repo as project_module
import app.db.repositories.security_test_repo as security_module
import app.db.repositories.test_case_repo as test_case_module
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.security_test_repo import SecurityTestCaseRepository
from app.db.repositories.test_case_repo import TestCaseRepository


class FakeCollection:
    def __init__(self) -> None:
        self.indexes: list[tuple[list[tuple[str, int]], dict]] = []

    async def create_index(self, keys, **options):
        self.indexes.append((keys, options))


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


@pytest.mark.asyncio
async def test_project_indexes_make_owner_name_unique(monkeypatch: pytest.MonkeyPatch) -> None:
    database = FakeDatabase()
    monkeypatch.setattr(project_module, "get_database", lambda: database)

    await ProjectRepository().ensure_indexes()

    assert ([('owner_id', 1), ('name', 1)], {'unique': True}) in database["projects"].indexes


@pytest.mark.asyncio
async def test_test_case_indexes_make_logical_id_unique_per_project(monkeypatch: pytest.MonkeyPatch) -> None:
    database = FakeDatabase()
    monkeypatch.setattr(test_case_module, "get_database", lambda: database)

    repository = TestCaseRepository("Demo")
    await repository.ensure_indexes()

    assert ([('project_id', 1), ('metadata.test_id', 1)], {'unique': True, 'sparse': True}) in database[repository.collection_name].indexes


@pytest.mark.asyncio
async def test_security_test_indexes_make_logical_id_unique_per_project(monkeypatch: pytest.MonkeyPatch) -> None:
    database = FakeDatabase()
    monkeypatch.setattr(security_module, "get_database", lambda: database)

    repository = SecurityTestCaseRepository("Demo")
    await repository.ensure_indexes()

    assert ([('project_id', 1), ('test_id', 1)], {'unique': True, 'sparse': True}) in database[repository.collection_name].indexes
