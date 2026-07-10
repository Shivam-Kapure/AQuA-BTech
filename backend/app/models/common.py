from __future__ import annotations

"""
Common helpers for working with MongoDB ObjectIds.

To avoid Pydantic v2 custom-type complexities, API models expose IDs as strings,
and repositories handle conversion to/from real ObjectId instances.
"""

from bson import ObjectId


def to_object_id(value: str | ObjectId | None) -> ObjectId | None:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    raise ValueError("Invalid ObjectId value")


