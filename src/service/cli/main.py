import os
import sys
import time

from service.cli.config import handle_config, load_server_url
from service.cli.executor import JsonArgumentParser, build_parser, execute_local
from service.cli.installer import install_client
from service.cli.output import render_payload
from service.cli.remote_client import execute_remote


def _extract_server(argv: list[str]) -> tuple[str | None, list[str]]:
    cleaned: list[str] = []
    server_url: str | None = None
    skip_next = False
    for index, item in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if item == "--server":
            if index + 1 < len(argv):
                server_url = argv[index + 1]
                skip_next = True
            continue
        if item.startswith("--server="):
            server_url = item.split("=", 1)[1]
            continue
        cleaned.append(item)
    return server_url, cleaned


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    json_output = "--json" in raw_argv
    if raw_argv and raw_argv[0] == "install-client":
        exit_code, payload = install_client(raw_argv[1:])
        print(render_payload(payload, json_output=json_output), end="")
        return exit_code
    if raw_argv and raw_argv[0] == "config":
        exit_code, payload = handle_config([item for item in raw_argv[1:] if item != "--json"])
        print(render_payload(payload, json_output=json_output), end="")
        return exit_code
    explicit_server, local_argv = _extract_server(raw_argv)
    server_url = explicit_server or os.environ.get("NEODEV_API_URL") or load_server_url()
    if server_url:
        exit_code, payload = execute_remote(server_url, local_argv)
    else:
        exit_code, payload = execute_local(local_argv)
    print(render_payload(payload, json_output=json_output), end="")
    if server_url and not json_output and _should_follow_project_init(payload):
        return _follow_project_init(server_url, payload)
    return exit_code


def _should_follow_project_init(payload: dict) -> bool:
    if payload.get("command") != "project create" or not payload.get("ok"):
        return False
    project = (payload.get("data") or {}).get("project") or {}
    init_result = project.get("init_result") or {}
    return bool(project.get("id")) and init_result.get("status") in {"queued", "running"}


def _follow_project_init(server_url: str, create_payload: dict) -> int:
    project = create_payload["data"]["project"]
    project_id = project["id"]
    seen_state: tuple | None = None
    while True:
        time.sleep(2)
        exit_code, payload = execute_remote(
            server_url,
            ["project", "init-status", "--project-id", str(project_id), "--json"],
        )
        text, state = _format_project_init_event(payload, project_id)
        if state != seen_state and text:
            print(text, end="")
            seen_state = state
        status = (((payload.get("data") or {}).get("init_status") or {}).get("status"))
        if exit_code != 0 or status in {"completed", "failed"}:
            return exit_code


def _format_project_init_event(payload: dict, project_id: int) -> tuple[str, tuple]:
    if not payload.get("ok"):
        return render_payload(payload), ("error", str(payload.get("errors")))
    init_status = (payload.get("data") or {}).get("init_status") or {}
    progress = init_status.get("progress") or {}
    status = init_status.get("status") or "unknown"
    stage = progress.get("stage") or status
    done = progress.get("done")
    total = progress.get("total")
    detail = progress.get("detail") or init_status.get("error_message") or ""
    state = (status, stage, done, total, detail)
    prefix = f"[project {project_id}] {stage}"
    if done is not None and total is not None:
        prefix += f" {done}/{total}"
    if status:
        prefix += f" ({status})"
    lines = [prefix]
    if detail:
        lines.append(f"  {detail}")
    for node in init_status.get("key_nodes") or []:
        lines.append(f"  - {node.get('label') or node.get('stage')}: {node.get('status')}")
    return "\n".join(lines) + "\n", state


if __name__ == "__main__":
    raise SystemExit(main())
