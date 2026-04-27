from fastapi import APIRouter
from pydantic import BaseModel, Field

from service.cli.executor import execute_local


router = APIRouter(prefix="", tags=["cli"])


class CliExecuteRequest(BaseModel):
    argv: list[str] = Field(default_factory=list)


class CliExecuteResponse(BaseModel):
    exit_code: int
    payload: dict


@router.post("/execute", response_model=CliExecuteResponse)
def execute_cli(body: CliExecuteRequest) -> CliExecuteResponse:
    exit_code, payload = execute_local(body.argv)
    return CliExecuteResponse(exit_code=exit_code, payload=payload)
