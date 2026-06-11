from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from service.cli.errors import CliError


@dataclass(frozen=True)
class WorkflowStepSpec:
    id: str
    command: str
    summary: str = ""
    run: Callable[[], dict[str, Any] | None] | None = None
    retry_hint: str | None = None


def run_workflow(
    *,
    scenario_id: str,
    stage: str,
    steps: list[WorkflowStepSpec],
    summary: dict[str, Any],
    closure_evidence: list[dict[str, Any]],
    next_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    executed_steps: list[dict[str, Any]] = []
    failed_step: str | None = None
    retry_hint: str | None = None

    for step in steps:
        if failed_step is not None:
            executed_steps.append(_skipped_step(step))
            continue

        try:
            executed_steps.append(_execute_step(step))
        except CliError as exc:
            failed_step = step.id
            retry_hint = step.retry_hint
            executed_steps.append(_failed_step(step, exc))
        except Exception as exc:  # pragma: no cover - defensive conversion
            failed_step = step.id
            retry_hint = step.retry_hint
            executed_steps.append(
                _failed_step(
                    step,
                    CliError(
                        category="internal_error",
                        message=str(exc),
                        details={"exception_type": type(exc).__name__},
                    ),
                )
            )

    payload: dict[str, Any] = {
        "scenario_id": scenario_id,
        "stage": stage,
        "steps": executed_steps,
        "summary": summary,
        "closure_evidence": closure_evidence,
        "next_actions": next_actions,
    }
    if failed_step is not None:
        payload["failed_step"] = failed_step
        if retry_hint:
            payload["retry_hint"] = retry_hint
    return payload


def _execute_step(step: WorkflowStepSpec) -> dict[str, Any]:
    result = step.run() if step.run else None
    result = result or {}
    status = str(result.get("status") or ("success" if step.run else "not_evaluated"))
    summary = str(result.get("summary") or step.summary or step.command)
    payload = {
        "id": step.id,
        "command": step.command,
        "status": status,
        "summary": summary,
    }
    evidence = result.get("evidence")
    if evidence is not None:
        payload["evidence"] = evidence
    return payload


def _failed_step(step: WorkflowStepSpec, exc: CliError) -> dict[str, Any]:
    return {
        "id": step.id,
        "command": step.command,
        "status": "failed",
        "summary": step.summary or step.command,
        "error": {
            "category": exc.category,
            "message": exc.message,
            "details": exc.details,
        },
    }


def _skipped_step(step: WorkflowStepSpec) -> dict[str, Any]:
    return {
        "id": step.id,
        "command": step.command,
        "status": "skipped",
        "summary": step.summary or step.command,
    }
