import json
import os
import sys

from service.cli.config import handle_config, load_server_url
from service.cli.executor import JsonArgumentParser, build_parser, execute_local
from service.cli.installer import install_client
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
    if raw_argv and raw_argv[0] == "install-client":
        exit_code, payload = install_client(raw_argv[1:])
        print(json.dumps(payload, ensure_ascii=False))
        return exit_code
    if raw_argv and raw_argv[0] == "config":
        exit_code, payload = handle_config(raw_argv[1:])
        print(json.dumps(payload, ensure_ascii=False))
        return exit_code
    explicit_server, local_argv = _extract_server(raw_argv)
    server_url = explicit_server or os.environ.get("NEODEV_API_URL") or load_server_url()
    if server_url:
        exit_code, payload = execute_remote(server_url, local_argv)
    else:
        exit_code, payload = execute_local(local_argv)
    if payload.get("command") == "help":
        text = (payload.get("data") or {}).get("text")
        if isinstance(text, str):
            print(text, end="" if text.endswith("\n") else "\n")
            return exit_code
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
