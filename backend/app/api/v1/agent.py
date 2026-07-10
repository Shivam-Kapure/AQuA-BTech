from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.agent_service import run_agent_once


router = APIRouter()


class AgentRunRequest(BaseModel):
    project_name: str
    url: str


class AgentRunResponse(BaseModel):
    agent_decision: dict
    effect: dict | None = None


@router.post("/run-once", response_model=AgentRunResponse)
async def run_agent_endpoint(payload: AgentRunRequest):
    """
    Run a single agent decision step for a project and URL.

    The agent (Phi-4-mini) decides whether to generate tests or do nothing.
    """
    result = await run_agent_once(
        project_name=payload.project_name,
        url=payload.url,
    )
    return AgentRunResponse(**result)

