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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) >= 3 and argv[0] == "config" and argv[1] == "set-server":
        _save_server_url(argv[2])
        print(json.dumps(_payload(True, "config set-server", {
            "server_url": argv[2],
            "config_path": str(_config_path()),
        }), ensure_ascii=False))
        return 0
    if argv == ["config", "show"]:
        print(json.dumps(_payload(True, "config show", {
            "server_url": _load_server_url(),
            "config_path": str(_config_path()),
        }), ensure_ascii=False))
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
        print(json.dumps(_payload(False, "remote cli execute", None, {
            "category": "invalid_argument",
            "message": "remote server is not configured; run: neodev config set-server <url>",
            "details": {},
        }), ensure_ascii=False))
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
        print(json.dumps(_payload(False, "remote cli execute", None, {
            "category": "internal_error",
            "message": "remote CLI request failed",
            "details": {"server_url": server_url, "error": str(exc)},
        }), ensure_ascii=False))
        return 10

    print(json.dumps(body.get("payload", body), ensure_ascii=False))
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
