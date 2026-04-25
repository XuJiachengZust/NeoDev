from service.cli.commands import cli
from service.cli.commands import product


def register_commands(subparsers) -> None:
    cli.register(subparsers)
    product.register(subparsers)
