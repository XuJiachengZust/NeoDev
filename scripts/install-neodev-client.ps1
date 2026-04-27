param(
    [string]$Server = "",
    [string]$InstallDir = "$env:USERPROFILE\.neodev\bin",
    [string]$ConfigDir = "$env:USERPROFILE\.neodev",
    [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"

function Find-Python {
    $candidates = @("python", "py")
    foreach ($candidate in $candidates) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
    }
    throw "Python was not found in PATH. Install Python 3.11+ before installing NeoDev CLI."
}

$python = Find-Python
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$clientPath = Join-Path $InstallDir "neodev_client.py"
$cmdPath = Join-Path $InstallDir "neodev.cmd"

$client = @'
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


CONFIG_DIR = Path(os.environ.get("NEODEV_CONFIG_DIR") or r"__CONFIG_DIR__")


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
        json.dumps({"server_url": server_url}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _payload(ok, command, data=None, error=None):
    return {
        "ok": ok,
        "command": command,
        "timestamp": None,
        "data": data,
        "errors": [] if error is None else [error],
    }


def _json_output(argv):
    return "--json" in argv


def _plain_scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _append_plain(lines, key, value, indent=0):
    prefix = "  " * indent
    if isinstance(value, dict):
        if not value:
            lines.append(f"{prefix}{key}: " + "{}")
            return
        lines.append(f"{prefix}{key}:")
        for child_key, child_value in value.items():
            _append_plain(lines, str(child_key), child_value, indent + 1)
        return
    if isinstance(value, list):
        if not value:
            lines.append(f"{prefix}{key}: []")
            return
        lines.append(f"{prefix}{key}:")
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}  -")
                _append_plain(lines, "value", item, indent + 2)
            else:
                lines.append(f"{prefix}  - {_plain_scalar(item)}")
        return
    lines.append(f"{prefix}{key}: {_plain_scalar(value)}")


def _render_payload(payload, json_output=False):
    if json_output:
        return json.dumps(payload, ensure_ascii=False) + "\n"
    if isinstance(payload, dict) and payload.get("command") == "help":
        text = (payload.get("data") or {}).get("text")
        if isinstance(text, str):
            return text if text.endswith("\n") else text + "\n"
    if not isinstance(payload, dict) or not payload.get("ok"):
        errors = payload.get("errors") if isinstance(payload, dict) else None
        if not errors:
            return "ERROR: command failed\n"
        lines = []
        for error in errors:
            lines.append(f"ERROR [{error.get('category') or 'error'}]: {error.get('message') or 'command failed'}")
            details = error.get("details") or {}
            if isinstance(details, dict):
                for key, value in details.items():
                    _append_plain(lines, f"details.{key}", value)
        return "\n".join(lines) + "\n"
    lines = [f"command: {payload.get('command', 'unknown')}", "ok: true"]
    data = payload.get("data") or {}
    message = data.get("message") if isinstance(data, dict) else None
    if isinstance(message, str) and message.strip():
        lines.insert(0, message)
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "message":
                continue
            _append_plain(lines, key, value)
    elif data:
        _append_plain(lines, "data", data)
    return "\n".join(lines) + "\n"


def _print_payload(payload, json_output=False):
    sys.stdout.write(_render_payload(payload, json_output=json_output))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_output = _json_output(argv)
    if len(argv) >= 3 and argv[0] == "config" and argv[1] == "set-server":
        _save_server_url(argv[2])
        _print_payload(_payload(True, "config set-server", {
            "server_url": argv[2],
            "config_path": str(_config_path()),
        }), json_output=json_output)
        return 0
    if argv[:2] == ["config", "show"] and all(item == "--json" for item in argv[2:]):
        _print_payload(_payload(True, "config show", {
            "server_url": _load_server_url(),
            "config_path": str(_config_path()),
        }), json_output=json_output)
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

    server_url = server_url or os.environ.get("NEODEV_API_URL") or _load_server_url()
    if not server_url:
        _print_payload(_payload(False, "remote cli execute", None, {
            "category": "invalid_argument",
            "message": "remote server is not configured; run: neodev config set-server <url>",
            "details": {},
        }), json_output=json_output)
        return 2

    request = urllib.request.Request(
        server_url.rstrip("/") + "/api/cli/execute",
        data=json.dumps({"argv": cleaned}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"))
        return 10
    except OSError as exc:
        _print_payload(_payload(False, "remote cli execute", None, {
            "category": "internal_error",
            "message": "remote CLI request failed",
            "details": {"server_url": server_url, "error": str(exc)},
        }), json_output=json_output)
        return 10

    payload = body.get("payload", body)
    _print_payload(payload, json_output=json_output)
    return int(body.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
'@

$client = $client.Replace("__CONFIG_DIR__", $ConfigDir.Replace("\", "\\"))
Set-Content -Path $clientPath -Value $client -Encoding UTF8
Set-Content -Path $cmdPath -Value "@echo off`r`n`"$python`" `"$clientPath`" %*`r`n" -Encoding ASCII

if ($Server) {
    & $python $clientPath config set-server $Server | Out-Host
}

if (-not $NoPathUpdate) {
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @()
    if ($currentPath) {
        $parts = $currentPath.Split(";") | Where-Object { $_ }
    }
    $exists = $false
    foreach ($part in $parts) {
        if ($part.TrimEnd("\").ToLowerInvariant() -eq $InstallDir.TrimEnd("\").ToLowerInvariant()) {
            $exists = $true
            break
        }
    }
    if (-not $exists) {
        $updated = (($parts + $InstallDir) -join ";")
        [Environment]::SetEnvironmentVariable("Path", $updated, "User")
    }
}

Write-Host "NeoDev CLI installed: $cmdPath"
Write-Host "Open a new terminal and run: neodev config show"
