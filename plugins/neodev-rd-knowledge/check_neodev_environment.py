import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _payload(ok: bool, data: dict | None = None, error: dict | None = None) -> dict:
    return {
        "ok": ok,
        "command": "neodev environment check",
        "timestamp": None,
        "data": data or {},
        "errors": [] if error is None else [error],
    }


def _error(category: str, message: str, details: dict | None = None) -> int:
    print(
        json.dumps(
            _payload(
                False,
                error={
                    "category": category,
                    "message": message,
                    "details": details or {},
                },
            ),
            ensure_ascii=False,
        )
    )
    return 2 if category == "invalid_argument" else 5


def _resolve_cli() -> list[str] | None:
    configured = os.environ.get("NEODEV_CLI")
    if configured:
        return [configured]
    found = shutil.which("neodev")
    if found:
        return [found]
    return None


def _run(cli: list[str], args: list[str]) -> tuple[int, dict | None, str]:
    proc = subprocess.run(
        [*cli, *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=300,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = None
    return proc.returncode, payload, proc.stderr.strip()


def main() -> int:
    cli = _resolve_cli()
    if not cli:
        return _error(
            "not_ready",
            "NeoDev CLI 未安装；请先运行 GitHub 一行安装命令 scripts/install-neodev-client.ps1。",
        )

    config_rc, config_payload, config_stderr = _run(cli, ["config", "show", "--json"])
    if config_rc != 0 or not config_payload or not config_payload.get("ok"):
        return _error(
            "not_ready",
            "NeoDev CLI 远程服务未配置；请运行 neodev config set-server <url>。",
            {"stderr": config_stderr, "payload": config_payload},
        )

    server_url = (config_payload.get("data") or {}).get("server_url")
    if not server_url:
        return _error(
            "not_ready",
            "NeoDev CLI 缺少远程服务地址；请运行 neodev config set-server <url>。",
            {"config_path": (config_payload.get("data") or {}).get("config_path")},
        )

    version_rc, version_payload, version_stderr = _run(cli, ["cli", "version-check", "--json"])
    if version_rc != 0 or not version_payload or not version_payload.get("ok"):
        return _error(
            "not_ready",
            "NeoDev 远程服务不可用或 CLI 版本检查失败。",
            {"stderr": version_stderr, "payload": version_payload},
        )

    version_data = version_payload.get("data") or {}
    if version_data.get("compatible") is not True:
        return _error(
            "version_mismatch",
            "NeoDev CLI、插件与 skill 契约版本不一致。",
            version_data,
        )

    print(
        json.dumps(
            _payload(
                True,
                {
                    "cli": " ".join(cli),
                    "server_url": server_url,
                    "version": version_data,
                },
            ),
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
