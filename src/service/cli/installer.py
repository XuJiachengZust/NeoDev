import argparse
import os
import stat
import sys
from pathlib import Path

from service.cli.config import save_server_url
from service.cli.output import build_success_payload


CLIENT_TEMPLATE = """\
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


CONFIG_DIR = Path(os.environ.get("NEODEV_CONFIG_DIR") or r"{config_dir}")


def _config_path():
    return CONFIG_DIR / "config.json"


def _load_server_url():
    try:
        payload = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("server_url")
    return value if isinstance(value, str) and value.strip() else None


def _save_server_url(server_url):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _config_path().write_text(
        json.dumps({{"server_url": server_url}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _success(command, data):
    return {{
        "ok": True,
        "command": command,
        "timestamp": None,
        "data": data,
        "errors": [],
    }}


def _error(message):
    return {{
        "ok": False,
        "command": "config",
        "timestamp": None,
        "data": None,
        "errors": [{{"category": "invalid_argument", "message": message, "details": {{}}}}],
    }}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) >= 3 and argv[0] == "config" and argv[1] == "set-server":
        _save_server_url(argv[2])
        print(json.dumps(_success("config set-server", {{
            "server_url": argv[2],
            "config_path": str(_config_path()),
        }}), ensure_ascii=False))
        return 0
    if argv == ["config", "show"]:
        print(json.dumps(_success("config show", {{
            "server_url": _load_server_url(),
            "config_path": str(_config_path()),
        }}), ensure_ascii=False))
        return 0

    server_url = None
    cleaned = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--server" and index + 1 < len(argv):
            server_url = argv[index + 1]
            index += 2
            continue
        if item.startswith("--server="):
            server_url = item.split("=", 1)[1]
            index += 1
            continue
        cleaned.append(item)
        index += 1
    argv = cleaned
    server_url = server_url or os.environ.get("NEODEV_API_URL") or _load_server_url()
    if not server_url:
        print(json.dumps(_error("remote server is not configured; run: neodev config set-server <url>"), ensure_ascii=False))
        return 2

    endpoint = server_url.rstrip("/") + "/api/cli/execute"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({{"argv": argv}}).encode("utf-8"),
        headers={{"Content-Type": "application/json"}},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"))
        return 10
    except OSError as exc:
        print(json.dumps({{
            "ok": False,
            "command": "remote cli execute",
            "timestamp": None,
            "data": None,
            "errors": [{{
                "category": "internal_error",
                "message": "remote CLI request failed",
                "details": {{"server_url": server_url, "error": str(exc)}},
            }}],
        }}, ensure_ascii=False))
        return 10
    print(json.dumps(body.get("payload", body), ensure_ascii=False))
    return int(body.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
"""


def install_client(argv: list[str]) -> tuple[int, dict]:
    parser = argparse.ArgumentParser(prog="neodev install-client")
    parser.add_argument("--server", dest="server_url")
    parser.add_argument("--bin-dir")
    parser.add_argument("--config-dir")
    parser.add_argument("--no-path-update", action="store_true")
    args = parser.parse_args(argv)

    bin_dir = Path(args.bin_dir).expanduser() if args.bin_dir else _default_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    config_dir = Path(args.config_dir).expanduser() if args.config_dir else _default_config_dir()

    client_path = bin_dir / "neodev_client.py"
    client_path.write_text(
        CLIENT_TEMPLATE.format(config_dir=str(config_dir)),
        encoding="utf-8",
    )
    if args.server_url:
        previous = os.environ.get("NEODEV_CONFIG_DIR")
        os.environ["NEODEV_CONFIG_DIR"] = str(config_dir)
        try:
            save_server_url(args.server_url)
        finally:
            if previous is None:
                os.environ.pop("NEODEV_CONFIG_DIR", None)
            else:
                os.environ["NEODEV_CONFIG_DIR"] = previous

    written = [client_path]
    if os.name == "nt":
        cmd_path = bin_dir / "neodev.cmd"
        cmd_path.write_text(
            f'@echo off\r\n"{sys.executable}" "{client_path}" %*\r\n',
            encoding="utf-8",
        )
        written.append(cmd_path)
    else:
        shell_path = bin_dir / "neodev"
        shell_path.write_text(
            f'#!/usr/bin/env sh\nexec "{sys.executable}" "{client_path}" "$@"\n',
            encoding="utf-8",
        )
        shell_path.chmod(shell_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        written.append(shell_path)

    path_updated = False
    if not args.no_path_update and os.name == "nt":
        path_updated = _ensure_user_path(bin_dir)

    return 0, build_success_payload(
        "install-client",
        {
            "server_url": args.server_url,
            "bin_dir": str(bin_dir),
            "config_dir": str(config_dir),
            "written": [str(path) for path in written],
            "path_updated": path_updated,
            "command": "neodev",
        },
    )


def _default_bin_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".neodev" / "bin"
    return Path.home() / ".local" / "bin"


def _default_config_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".neodev"
    return Path.home() / ".config" / "neodev"


def _ensure_user_path(bin_dir: Path) -> bool:
    try:
        import winreg
    except ImportError:
        return False
    target = str(bin_dir)
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    ) as key:
        try:
            current, value_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, value_type = "", winreg.REG_EXPAND_SZ
        parts = [part for part in current.split(";") if part]
        if any(part.lower() == target.lower() for part in parts):
            return False
        updated = ";".join([*parts, target])
        winreg.SetValueEx(key, "Path", 0, value_type, updated)
    return True
