import argparse
import contextlib
import io

from service.cli.commands import register_commands
from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload, build_success_payload


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliError(category="invalid_argument", message=message)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="neodev")
    parser.add_argument("--json", action="store_true", dest="json_output")
    subparsers = parser.add_subparsers(dest="command_group", required=True)
    register_commands(subparsers)
    return parser


def execute_local(argv: list[str] | None = None) -> tuple[int, dict]:
    parser = build_parser()
    args = None
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            args = parser.parse_args(argv)
        payload = args.handler(args)
        return 0, payload
    except SystemExit as exc:
        help_text = stdout.getvalue()
        if exc.code == 0 and help_text:
            return 0, build_success_payload("help", {"text": help_text})
        raise
    except CliError as exc:
        command = getattr(args, "command_name", "unknown") if args is not None else "unknown"
        return error_to_exit_code(exc), build_error_payload(command, exc)
