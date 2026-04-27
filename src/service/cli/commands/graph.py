from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.services import graph_semantic_search_service
from service.services import product_service
from service.services import product_version_service


def register(subparsers) -> None:
    graph_parser = subparsers.add_parser("graph")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)

    semantic_parser = graph_subparsers.add_parser("semantic-search")
    _add_version_locator(semantic_parser)
    semantic_parser.add_argument("--query", required=True)
    semantic_parser.add_argument("--top-k", type=int, default=5)
    semantic_parser.add_argument("--json", action="store_true", dest="json_output")
    semantic_parser.set_defaults(
        handler=handle_semantic_search,
        command_name="graph semantic-search",
    )


def _add_product_locator(parser) -> None:
    parser.add_argument("--product-id", type=int)
    parser.add_argument("--product-code")


def _add_version_locator(parser) -> None:
    _add_product_locator(parser)
    parser.add_argument("--version-id", type=int)
    parser.add_argument("--version-name")


def _with_db(callback):
    try:
        with closing(psycopg2.connect(get_database_url())) as conn:
            return callback(conn)
    except CliError:
        raise
    except graph_semantic_search_service.GraphSemanticSearchError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except psycopg2.Error as exc:
        raise CliError(
            category="internal_error",
            message="database operation failed",
            details={"database_error": str(exc)},
        ) from exc


def handle_semantic_search(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        result = graph_semantic_search_service.semantic_search(
            conn,
            product_version_id=version["id"],
            query=args.query,
            top_k=args.top_k,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def _resolve_product(conn, args) -> dict:
    product_id = getattr(args, "product_id", None)
    product_code = getattr(args, "product_code", None)
    if product_id is None and not product_code:
        raise CliError(
            category="invalid_argument",
            message="provide --product-id or --product-code",
        )
    if product_id is not None and product_code:
        raise CliError(
            category="invalid_argument",
            message="provide only one product locator",
        )
    if product_id is not None:
        product = product_service.get_product(conn, product_id)
    else:
        product = product_service.get_product_by_code(conn, product_code)
    if not product:
        raise CliError(category="not_found", message="product not found")
    return product


def _resolve_version(conn, args) -> dict:
    version_id = getattr(args, "version_id", None)
    version_name = getattr(args, "version_name", None)
    if version_id is None and not version_name:
        raise CliError(
            category="invalid_argument",
            message="provide --version-id or --version-name",
        )
    if version_id is not None and version_name:
        raise CliError(
            category="invalid_argument",
            message="provide only one version locator",
        )
    if version_id is not None:
        version = product_version_service.get_version(conn, version_id)
        if not version:
            raise CliError(category="not_found", message="product version not found")
        return version
    product = _resolve_product(conn, args)
    version = product_version_service.get_version_by_name(conn, product["id"], version_name)
    if not version:
        raise CliError(category="not_found", message="product version not found")
    return version
