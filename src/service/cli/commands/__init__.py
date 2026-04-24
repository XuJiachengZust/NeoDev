from service.cli.commands import cli


def register_commands(subparsers) -> None:
    cli.register(subparsers)
