from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.services import graph_impact_service
from service.services import graph_query_service
from service.services import graph_refresh_service
from service.services import graph_semantic_search_service
from service.services import product_service
from service.services import product_version_service
from service.services import project_service


def register(subparsers) -> None:
    graph_parser = subparsers.add_parser("graph")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)

    impact_parser = graph_subparsers.add_parser("impact")
    impact_parser.add_argument("--change-id", type=int)
    impact_parser.add_argument("--doc-change-id")
    impact_parser.add_argument("--json", action="store_true", dest="json_output")
    impact_parser.set_defaults(
        handler=handle_impact,
        command_name="graph impact",
    )

    refresh_parser = graph_subparsers.add_parser("refresh-nodes")
    _add_version_locator(refresh_parser)
    _add_project_locator(refresh_parser)
    refresh_parser.add_argument("--branch", required=True)
    refresh_parser.add_argument("--node-id", action="append", dest="node_ids")
    refresh_parser.add_argument("--path", action="append", dest="paths")
    refresh_parser.add_argument("--commit-sha")
    refresh_parser.add_argument("--json", action="store_true", dest="json_output")
    refresh_parser.set_defaults(
        handler=handle_refresh_nodes,
        command_name="graph refresh-nodes",
    )

    semantic_parser = graph_subparsers.add_parser("semantic-search")
    _add_version_locator(semantic_parser)
    semantic_parser.add_argument("--query", required=True)
    semantic_parser.add_argument("--top-k", type=int, default=5)
    semantic_parser.add_argument("--json", action="store_true", dest="json_output")
    semantic_parser.set_defaults(
        handler=handle_semantic_search,
        command_name="graph semantic-search",
    )

    entity_parser = graph_subparsers.add_parser("entity-context")
    _add_version_locator(entity_parser)
    _add_project_locator(entity_parser)
    entity_parser.add_argument("--branch", required=True)
    entity_parser.add_argument("--entity-id", required=True)
    entity_parser.add_argument("--depth", type=int, default=1)
    entity_parser.add_argument("--json", action="store_true", dest="json_output")
    entity_parser.set_defaults(
        handler=handle_entity_context,
        command_name="graph entity-context",
    )

    chain_parser = graph_subparsers.add_parser("get-chain")
    _add_version_locator(chain_parser)
    _add_project_locator(chain_parser)
    chain_parser.add_argument("--branch", required=True)
    chain_parser.add_argument("--start-node")
    chain_parser.add_argument("--file-path")
    chain_parser.add_argument("--symbol")
    chain_parser.add_argument("--commit-sha")
    chain_parser.add_argument("--depth", type=int, default=1)
    chain_parser.add_argument("--json", action="store_true", dest="json_output")
    chain_parser.set_defaults(
        handler=handle_get_chain,
        command_name="graph get-chain",
    )


def _add_product_locator(parser) -> None:
    parser.add_argument("--product-id", type=int)
    parser.add_argument("--product-code")


def _add_version_locator(parser) -> None:
    _add_product_locator(parser)
    parser.add_argument("--version-id", type=int)
    parser.add_argument("--version-name")


def _add_project_locator(parser) -> None:
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--project-name")


def _with_db(callback):
    try:
        with closing(psycopg2.connect(get_database_url())) as conn:
            return callback(conn)
    except CliError:
        raise
    except graph_impact_service.GraphImpactError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except graph_semantic_search_service.GraphSemanticSearchError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except graph_query_service.GraphQueryError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except graph_refresh_service.GraphRefreshError as exc:
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


def handle_impact(args) -> dict:
    def run(conn):
        result = graph_impact_service.doc_change_impact(
            conn,
            change_id=args.change_id,
            doc_change_id=args.doc_change_id,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_refresh_nodes(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        project = _resolve_project(conn, args)
        result = graph_refresh_service.refresh_nodes(
            conn,
            product_version_id=version["id"],
            project_id=project["id"],
            branch=args.branch,
            node_ids=args.node_ids,
            paths=args.paths,
            commit_sha=args.commit_sha,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


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


def handle_entity_context(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        project = _resolve_project(conn, args)
        result = graph_query_service.entity_context(
            conn,
            product_version_id=version["id"],
            project_id=project["id"],
            branch=args.branch,
            entity_id=args.entity_id,
            depth=args.depth,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_get_chain(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        project = _resolve_project(conn, args)
        result = graph_query_service.get_chain(
            conn,
            product_version_id=version["id"],
            project_id=project["id"],
            branch=args.branch,
            start_node=args.start_node,
            file_path=args.file_path,
            symbol=args.symbol,
            commit_sha=args.commit_sha,
            depth=args.depth,
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


def _resolve_project(conn, args) -> dict:
    project_id = getattr(args, "project_id", None)
    project_name = getattr(args, "project_name", None)
    if project_id is None and not project_name:
        raise CliError(
            category="invalid_argument",
            message="provide --project-id or --project-name",
        )
    if project_id is not None and project_name:
        raise CliError(
            category="invalid_argument",
            message="provide only one project locator",
        )
    if project_id is not None:
        project = project_service.get_project(conn, project_id)
        if not project:
            raise CliError(category="not_found", message="project not found")
        return project
    matches = project_service.find_projects_by_name(conn, project_name)
    if not matches:
        raise CliError(category="not_found", message="project not found")
    if len(matches) > 1:
        raise CliError(
            category="conflict",
            message="project name is ambiguous",
            details={"project_name": project_name, "matches": [row["id"] for row in matches]},
        )
    return matches[0]
