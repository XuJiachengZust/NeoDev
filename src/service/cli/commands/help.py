from service.cli.command_metadata import get_command_metadata_payload
from service.cli.help_renderer import render_all_help, render_default_help
from service.cli.output import build_success_payload


def register(subparsers) -> None:
    help_parser = subparsers.add_parser("help")
    help_parser.add_argument("--all", action="store_true", dest="show_all")
    help_parser.add_argument("--json", action="store_true", dest="json_output")
    help_parser.set_defaults(handler=handle_help, command_name="help")


def handle_help(args) -> dict:
    if args.show_all:
        data = get_command_metadata_payload()
        data["text"] = render_all_help()
        return build_success_payload("help all", data)
    return build_success_payload("help", {"text": render_default_help()})
