from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.services import graph_impact_service
from service.services import graph_management_service
from service.services import graph_query_service
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

    type_parser = graph_subparsers.add_parser("type")
    type_subparsers = type_parser.add_subparsers(dest="type_domain", required=True)
    node_type_parser = type_subparsers.add_parser("node")
    node_type_subparsers = node_type_parser.add_subparsers(dest="type_action", required=True)
    _register_node_type_commands(node_type_subparsers)
    edge_type_parser = type_subparsers.add_parser("edge")
    edge_type_subparsers = edge_type_parser.add_subparsers(dest="type_action", required=True)
    _register_edge_type_commands(edge_type_subparsers)

    node_parser = graph_subparsers.add_parser("node")
    node_subparsers = node_parser.add_subparsers(dest="node_action", required=True)
    _register_node_commands(node_subparsers)

    edge_parser = graph_subparsers.add_parser("edge")
    edge_subparsers = edge_parser.add_subparsers(dest="edge_action", required=True)
    _register_edge_commands(edge_subparsers)


def _register_node_type_commands(subparsers) -> None:
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--project-id", type=int, required=True)
    add_parser.add_argument("--key", required=True)
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--description")
    add_parser.add_argument("--json", action="store_true", dest="json_output")
    add_parser.set_defaults(handler=handle_node_type_add, command_name="graph type node add")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--project-id", type=int, required=True)
    list_parser.add_argument("--json", action="store_true", dest="json_output")
    list_parser.set_defaults(handler=handle_node_type_list, command_name="graph type node list")

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("--project-id", type=int, required=True)
    archive_parser.add_argument("--key", required=True)
    archive_parser.add_argument("--json", action="store_true", dest="json_output")
    archive_parser.set_defaults(handler=handle_node_type_archive, command_name="graph type node archive")


def _register_edge_type_commands(subparsers) -> None:
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--project-id", type=int, required=True)
    add_parser.add_argument("--key", required=True)
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--description")
    add_parser.add_argument("--allowed-from-type", action="append", default=[])
    add_parser.add_argument("--allowed-to-type", action="append", default=[])
    add_parser.add_argument("--cross-project-allowed", action="store_true")
    add_parser.add_argument("--json", action="store_true", dest="json_output")
    add_parser.set_defaults(handler=handle_edge_type_add, command_name="graph type edge add")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--project-id", type=int, required=True)
    list_parser.add_argument("--json", action="store_true", dest="json_output")
    list_parser.set_defaults(handler=handle_edge_type_list, command_name="graph type edge list")

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("--project-id", type=int, required=True)
    archive_parser.add_argument("--key", required=True)
    archive_parser.add_argument("--json", action="store_true", dest="json_output")
    archive_parser.set_defaults(handler=handle_edge_type_archive, command_name="graph type edge archive")


def _register_node_commands(subparsers) -> None:
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--project-id", type=int, required=True)
    add_parser.add_argument("--branch", required=True)
    add_parser.add_argument("--node-id", required=True)
    add_parser.add_argument("--type", required=True)
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--prop", action="append", default=[])
    add_parser.add_argument("--json", action="store_true", dest="json_output")
    add_parser.set_defaults(handler=handle_node_add, command_name="graph node add")

    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--project-id", type=int, required=True)
    update_parser.add_argument("--branch", required=True)
    update_parser.add_argument("--node-id", required=True)
    update_parser.add_argument("--type")
    update_parser.add_argument("--name")
    update_parser.add_argument("--prop", action="append", default=[])
    update_parser.add_argument("--status")
    update_parser.add_argument("--json", action="store_true", dest="json_output")
    update_parser.set_defaults(handler=handle_node_update, command_name="graph node update")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("--project-id", type=int, required=True)
    delete_parser.add_argument("--branch", required=True)
    delete_parser.add_argument("--node-id", required=True)
    delete_parser.add_argument("--json", action="store_true", dest="json_output")
    delete_parser.set_defaults(handler=handle_node_delete, command_name="graph node delete")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--project-id", type=int, required=True)
    show_parser.add_argument("--node-id", required=True)
    show_parser.add_argument("--json", action="store_true", dest="json_output")
    show_parser.set_defaults(handler=handle_node_show, command_name="graph node show")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--project-id", type=int, required=True)
    list_parser.add_argument("--type")
    list_parser.add_argument("--json", action="store_true", dest="json_output")
    list_parser.set_defaults(handler=handle_node_list, command_name="graph node list")


def _register_edge_commands(subparsers) -> None:
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--project-id", type=int, required=True)
    add_parser.add_argument("--branch", required=True)
    add_parser.add_argument("--edge-id", required=True)
    add_parser.add_argument("--from-node-id", required=True)
    add_parser.add_argument("--from-project-id", type=int)
    add_parser.add_argument("--to-node-id", required=True)
    add_parser.add_argument("--to-project-id", type=int)
    add_parser.add_argument("--type", required=True)
    add_parser.add_argument("--prop", action="append", default=[])
    add_parser.add_argument("--json", action="store_true", dest="json_output")
    add_parser.set_defaults(handler=handle_edge_add, command_name="graph edge add")

    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--project-id", type=int, required=True)
    update_parser.add_argument("--branch", required=True)
    update_parser.add_argument("--edge-id", required=True)
    update_parser.add_argument("--type")
    update_parser.add_argument("--prop", action="append", default=[])
    update_parser.add_argument("--status")
    update_parser.add_argument("--json", action="store_true", dest="json_output")
    update_parser.set_defaults(handler=handle_edge_update, command_name="graph edge update")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("--project-id", type=int, required=True)
    delete_parser.add_argument("--branch", required=True)
    delete_parser.add_argument("--edge-id", required=True)
    delete_parser.add_argument("--json", action="store_true", dest="json_output")
    delete_parser.set_defaults(handler=handle_edge_delete, command_name="graph edge delete")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--project-id", type=int, required=True)
    show_parser.add_argument("--edge-id", required=True)
    show_parser.add_argument("--json", action="store_true", dest="json_output")
    show_parser.set_defaults(handler=handle_edge_show, command_name="graph edge show")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--project-id", type=int, required=True)
    list_parser.add_argument("--node-id")
    list_parser.add_argument("--type")
    list_parser.add_argument("--json", action="store_true", dest="json_output")
    list_parser.set_defaults(handler=handle_edge_list, command_name="graph edge list")


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
    conn = None
    try:
        with closing(psycopg2.connect(get_database_url())) as conn:
            result = callback(conn)
            conn.commit()
            return result
    except CliError:
        if conn is not None:
            conn.rollback()
        raise
    except graph_impact_service.GraphImpactError as exc:
        if conn is not None:
            conn.rollback()
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except graph_management_service.GraphManagementError as exc:
        if conn is not None:
            conn.rollback()
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except graph_query_service.GraphQueryError as exc:
        if conn is not None:
            conn.rollback()
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except psycopg2.Error as exc:
        if conn is not None:
            conn.rollback()
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


def handle_graph_management_placeholder(args) -> dict:
    raise CliError(
        category="not_ready",
        message="graph management command is not implemented yet",
        details={"command": args.command_name},
    )


def handle_node_type_add(args) -> dict:
    def run(conn):
        node_type = graph_management_service.create_node_type(
            conn,
            project_id=args.project_id,
            type_key=args.key,
            name=args.name,
            description=args.description,
        )
        return build_success_payload(args.command_name, {"node_type": node_type})

    return _with_db(run)


def handle_node_type_list(args) -> dict:
    def run(conn):
        result = graph_management_service.list_node_types(conn, project_id=args.project_id)
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_node_type_archive(args) -> dict:
    def run(conn):
        node_type = graph_management_service.archive_node_type(
            conn,
            project_id=args.project_id,
            type_key=args.key,
        )
        return build_success_payload(args.command_name, {"node_type": node_type})

    return _with_db(run)


def handle_edge_type_add(args) -> dict:
    def run(conn):
        edge_type = graph_management_service.create_relation_type(
            conn,
            project_id=args.project_id,
            type_key=args.key,
            name=args.name,
            description=args.description,
            allowed_from_types=args.allowed_from_type,
            allowed_to_types=args.allowed_to_type,
            cross_project_allowed=args.cross_project_allowed,
        )
        return build_success_payload(args.command_name, {"edge_type": edge_type})

    return _with_db(run)


def handle_edge_type_list(args) -> dict:
    def run(conn):
        result = graph_management_service.list_relation_types(conn, project_id=args.project_id)
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_edge_type_archive(args) -> dict:
    def run(conn):
        edge_type = graph_management_service.archive_relation_type(
            conn,
            project_id=args.project_id,
            type_key=args.key,
        )
        return build_success_payload(args.command_name, {"edge_type": edge_type})

    return _with_db(run)


def handle_node_add(args) -> dict:
    def run(conn):
        node = graph_management_service.create_node(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            node_id=args.node_id,
            type_key=args.type,
            name=args.name,
            properties=_parse_props(args.prop),
        )
        return build_success_payload(args.command_name, {"node": node})

    return _with_db(run)


def handle_node_update(args) -> dict:
    updates = _collect_updates(
        type_key=args.type,
        name=args.name,
        properties=_parse_props(args.prop) if args.prop else None,
        status=args.status,
    )

    def run(conn):
        node = graph_management_service.update_node(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            node_id=args.node_id,
            updates=updates,
        )
        return build_success_payload(args.command_name, {"node": node})

    return _with_db(run)


def handle_node_delete(args) -> dict:
    def run(conn):
        node = graph_management_service.archive_node(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            node_id=args.node_id,
        )
        return build_success_payload(args.command_name, {"node": node})

    return _with_db(run)


def handle_node_show(args) -> dict:
    def run(conn):
        node = graph_management_service.get_node(
            conn,
            project_id=args.project_id,
            node_id=args.node_id,
        )
        return build_success_payload(args.command_name, {"node": node})

    return _with_db(run)


def handle_node_list(args) -> dict:
    def run(conn):
        result = graph_management_service.list_nodes(
            conn,
            project_id=args.project_id,
            type_key=args.type,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_edge_add(args) -> dict:
    def run(conn):
        edge = graph_management_service.create_edge(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            edge_id=args.edge_id,
            from_node_id=args.from_node_id,
            from_project_id=getattr(args, "from_project_id", None),
            to_node_id=args.to_node_id,
            to_project_id=getattr(args, "to_project_id", None),
            type_key=args.type,
            properties=_parse_props(args.prop),
        )
        return build_success_payload(args.command_name, {"edge": edge})

    return _with_db(run)


def handle_edge_update(args) -> dict:
    updates = _collect_updates(
        type_key=args.type,
        properties=_parse_props(args.prop) if args.prop else None,
        status=args.status,
    )

    def run(conn):
        edge = graph_management_service.update_edge(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            edge_id=args.edge_id,
            updates=updates,
        )
        return build_success_payload(args.command_name, {"edge": edge})

    return _with_db(run)


def handle_edge_delete(args) -> dict:
    def run(conn):
        edge = graph_management_service.archive_edge(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            edge_id=args.edge_id,
        )
        return build_success_payload(args.command_name, {"edge": edge})

    return _with_db(run)


def handle_edge_show(args) -> dict:
    def run(conn):
        edge = graph_management_service.get_edge(
            conn,
            project_id=args.project_id,
            edge_id=args.edge_id,
        )
        return build_success_payload(args.command_name, {"edge": edge})

    return _with_db(run)


def handle_edge_list(args) -> dict:
    def run(conn):
        result = graph_management_service.list_edges(
            conn,
            project_id=args.project_id,
            node_id=args.node_id,
            type_key=args.type,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def _parse_props(values: list[str]) -> dict[str, str]:
    properties: dict[str, str] = {}
    for raw in values or []:
        if "=" not in raw:
            raise CliError(
                category="invalid_argument",
                message="property must use key=value format",
                details={"property": raw},
            )
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise CliError(
                category="invalid_argument",
                message="property key is required",
                details={"property": raw},
            )
        properties[key] = value
    return properties


def _collect_updates(**kwargs) -> dict:
    updates = {key: value for key, value in kwargs.items() if value is not None}
    if not updates:
        raise CliError(
            category="invalid_argument",
            message="provide at least one field to update",
        )
    return updates


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
