import json
import os
from pathlib import Path

from service.cli.output import build_success_payload


def config_dir() -> Path:
    override = os.environ.get("NEODEV_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".neodev"
    return Path.home() / ".config" / "neodev"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_server_url() -> str | None:
    path = config_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    server_url = payload.get("server_url")
    return server_url if isinstance(server_url, str) and server_url.strip() else None


def save_server_url(server_url: str) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"server_url": server_url}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def handle_config(argv: list[str]) -> tuple[int, dict]:
    if len(argv) >= 2 and argv[0] == "set-server":
        path = save_server_url(argv[1])
        return 0, build_success_payload(
            "config set-server",
            {"server_url": argv[1], "config_path": str(path)},
        )
    if argv == ["show"]:
        return 0, build_success_payload(
            "config show",
            {"server_url": load_server_url(), "config_path": str(config_path())},
        )
    return 2, {
        "ok": False,
        "command": "config",
        "timestamp": None,
        "data": None,
        "errors": [
            {
                "category": "invalid_argument",
                "message": "usage: neodev config set-server <url> | neodev config show",
                "details": {},
            }
        ],
    }
