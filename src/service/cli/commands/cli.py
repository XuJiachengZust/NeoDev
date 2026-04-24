from service.cli.output import build_success_payload


def register(subparsers) -> None:
    cli_parser = subparsers.add_parser("cli")
    cli_subparsers = cli_parser.add_subparsers(dest="cli_command", required=True)

    version_parser = cli_subparsers.add_parser("version-check")
    version_parser.add_argument("--json", action="store_true", dest="json_output")
    version_parser.set_defaults(handler=handle_version_check, command_name="cli version-check")


def handle_version_check(args) -> dict:
    return build_success_payload(
        command=args.command_name,
        data={
            "cli_version": "dev",
            "plugin_version": None,
            "skill_version": None,
            "compatible": True,
            "update_available": False,
            "updated": False,
            "target_version": "dev",
            "message": "CLI 基础壳层已就绪，插件与 skill 版本联动待后续任务接入。",
        },
    )
