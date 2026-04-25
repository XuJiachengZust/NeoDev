from service.cli.commands import cli
from service.cli.commands import doc
from service.cli.commands import product


def register_commands(subparsers) -> None:
    cli.register(subparsers)
    doc.register(subparsers)
    product.register(subparsers)
