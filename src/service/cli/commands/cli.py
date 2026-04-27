import json
from pathlib import Path

from service.cli.output import build_success_payload


REPO_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_MANIFEST = REPO_ROOT / "plugins" / "neodev-rd-knowledge" / ".codex-plugin" / "plugin.json"
WORKFLOW_CONTRACT = REPO_ROOT / "plugins" / "neodev-rd-knowledge" / "workflows" / "core-workflows.json"


def register(subparsers) -> None:
    cli_parser = subparsers.add_parser("cli")
    cli_subparsers = cli_parser.add_subparsers(dest="cli_command", required=True)

    version_parser = cli_subparsers.add_parser("version-check")
    version_parser.add_argument("--json", action="store_true", dest="json_output")
    version_parser.set_defaults(handler=handle_version_check, command_name="cli version-check")


def handle_version_check(args) -> dict:
    plugin_version = _read_version(PLUGIN_MANIFEST)
    skill_version = _read_version(WORKFLOW_CONTRACT)
    target_version = plugin_version or skill_version or "dev"
    compatible = bool(plugin_version and skill_version and plugin_version == skill_version)
    return build_success_payload(
        command=args.command_name,
        data={
            "cli_version": "dev",
            "plugin_version": plugin_version,
            "skill_version": skill_version,
            "compatible": compatible,
            "update_available": False,
            "updated": False,
            "target_version": target_version,
            "message": _version_message(compatible, plugin_version, skill_version),
        },
    )


def _read_version(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = payload.get("version")
    return version if isinstance(version, str) and version else None


def _version_message(compatible: bool, plugin_version: str | None, skill_version: str | None) -> str:
    if compatible:
        return "CLI、插件与 skill 契约版本一致。"
    return (
        "CLI、插件与 skill 契约版本不一致；"
        f"plugin_version={plugin_version!r}, skill_version={skill_version!r}。"
    )
