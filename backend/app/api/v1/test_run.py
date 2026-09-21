from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.test_run_service import resume_single_test, run_single_test
from app.core.auth import AuthenticatedUser, get_current_user, get_route_jwt

router = APIRouter()


class ResumePayload(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)


@router.post("/{project_name}/{test_id}")
async def run_one_test(
    project_name: str,
    test_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    route_jwt: str | None = Depends(get_route_jwt),
):
    """
    Run a single test case for the given project.
    test_id can be the MongoDB _id or the logical id (e.g. TC001 from metadata.test_id).
    On completion returns status: passed | failed | waiting, and failure_reason if failed.
    """
    result = await run_single_test(
        project_name=project_name, test_id=test_id, owner_id=current_user.id, route_jwt=route_jwt
    )

    if result.get("error") == "project_not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    if result.get("error") == "test_not_found":
        raise HTTPException(status_code=404, detail="Test case not found")

    return {
        "status": result["status"],
        "failure_reason": result.get("failure_reason"),
        "test_id": result.get("test_id"),
        "test_name": result.get("test_name"),
        "script_path": result.get("script_path"),
        "generation_mode": result.get("generation_mode"),
        "dom": result.get("dom"),
        "required_inputs": result.get("required_inputs"),
    }


@router.post("/{project_name}/{test_id}/resume")
async def resume_one_test(
    project_name: str,
    test_id: str,
    payload: ResumePayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    route_jwt: str | None = Depends(get_route_jwt),
):
    result = await resume_single_test(
        project_name=project_name,
        test_id=test_id,
        inputs=payload.inputs or {},
        owner_id=current_user.id,
        route_jwt=route_jwt,
    )

    if result.get("error") == "project_not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    if result.get("error") == "test_not_found":
        raise HTTPException(status_code=404, detail="Test case not found")

    return {
        "status": result["status"],
        "failure_reason": result.get("failure_reason"),
        "test_id": result.get("test_id"),
        "test_name": result.get("test_name"),
        "script_path": result.get("script_path"),
        "generation_mode": result.get("generation_mode"),
        "dom": result.get("dom"),
        "required_inputs": result.get("required_inputs"),
    }
