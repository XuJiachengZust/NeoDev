from service.cli.commands import cli
from service.cli.commands import doc
from service.cli.commands import git
from service.cli.commands import graph
from service.cli.commands import project
from service.cli.commands import product


def register_commands(subparsers) -> None:
    cli.register(subparsers)
    doc.register(subparsers)
    git.register(subparsers)
    graph.register(subparsers)
    project.register(subparsers)
    product.register(subparsers)
