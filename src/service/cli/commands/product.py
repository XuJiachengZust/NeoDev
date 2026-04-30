import argparse
import json
from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.repositories import branch_graph_repository as branch_graph_repo
from service.services import branch_analysis_service
from service.services import product_service
from service.services import product_version_service
from service.services import project_service


def register(subparsers) -> None:
    product_parser = subparsers.add_parser("product")
    product_subparsers = product_parser.add_subparsers(dest="product_command", required=True)

    create_parser = product_subparsers.add_parser("create")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--product-code", "--code", dest="product_code")
    create_parser.add_argument("--description")
    create_parser.add_argument("--owner")
    create_parser.add_argument("--json", action="store_true", dest="json_output")
    create_parser.set_defaults(handler=handle_product_create, command_name="product create")

    update_parser = product_subparsers.add_parser("update")
    _add_product_locator(update_parser)
    update_parser.add_argument("--name")
    update_parser.add_argument("--new-product-code", dest="new_product_code")
    update_parser.add_argument("--description")
    update_parser.add_argument("--owner")
    update_parser.add_argument("--status")
    update_parser.add_argument("--json", action="store_true", dest="json_output")
    update_parser.set_defaults(handler=handle_product_update, command_name="product update")

    show_parser = product_subparsers.add_parser("show")
    _add_product_locator(show_parser)
    show_parser.add_argument("--json", action="store_true", dest="json_output")
    show_parser.set_defaults(handler=handle_product_show, command_name="product show")

    version_parser = product_subparsers.add_parser("version")
    version_subparsers = version_parser.add_subparsers(
        dest="version_command",
        required=True,
        metavar="{create,show,bind-branch,link-code,code-facts}",
    )

    version_create_parser = version_subparsers.add_parser("create")
    _add_product_locator(version_create_parser)
    version_create_parser.add_argument("--version-name", required=True)
    version_create_parser.add_argument("--description")
    version_create_parser.add_argument("--status", default="planning")
    version_create_parser.add_argument("--release-date")
    version_create_parser.add_argument("--json", action="store_true", dest="json_output")
    version_create_parser.set_defaults(
        handler=handle_version_create,
        command_name="product version create",
    )

    version_show_parser = version_subparsers.add_parser("show")
    _add_version_locator(version_show_parser)
    version_show_parser.add_argument("--json", action="store_true", dest="json_output")
    version_show_parser.set_defaults(
        handler=handle_version_show,
        command_name="product version show",
    )

    bind_parser = version_subparsers.add_parser("bind-branch")
    _add_version_locator(bind_parser)
    _add_project_locator(bind_parser)
    bind_parser.add_argument("--branch", required=True)
    bind_parser.add_argument("--json", action="store_true", dest="json_output")
    bind_parser.set_defaults(
        handler=handle_version_bind_branch,
        command_name="product version bind-branch",
    )

    link_code_parser = version_subparsers.add_parser("link-code")
    _add_version_locator(link_code_parser)
    _add_project_locator(link_code_parser, prefix="code-")
    link_code_parser.add_argument("--doc-id")
    link_code_parser.add_argument("--doc-node-id")
    link_code_parser.add_argument("--code-node-id")
    link_code_parser.add_argument("--locator-json")
    link_code_parser.add_argument("--relation-type")
    link_code_parser.add_argument("--unlink", action="store_true")
    link_code_parser.add_argument("--link-id", type=int)
    link_code_parser.add_argument("--source", default="manual")
    link_code_parser.add_argument("--confidence", type=float)
    link_code_parser.add_argument("--json", action="store_true", dest="json_output")
    link_code_parser.set_defaults(
        handler=handle_version_link_code,
        command_name="product version link-code",
    )

    code_facts_parser = version_subparsers.add_parser("code-facts")
    _add_version_locator(code_facts_parser)
    code_facts_parser.add_argument("--doc-id")
    code_facts_parser.add_argument("--node-type", action="append", dest="node_types")
    code_facts_parser.add_argument("--json", action="store_true", dest="json_output")
    code_facts_parser.set_defaults(
        handler=handle_version_code_facts,
        command_name="product version code-facts",
    )

    analyze_parser = version_subparsers.add_parser("analyze", help=argparse.SUPPRESS)
    _add_version_locator(analyze_parser)
    _add_project_locator(analyze_parser)
    analyze_parser.add_argument("--branch", required=True)
    analyze_parser.add_argument("--force", action="store_true")
    analyze_parser.add_argument("--json", action="store_true", dest="json_output")
    analyze_parser.set_defaults(
        handler=handle_version_analyze,
        command_name="product version analyze",
    )

    status_parser = version_subparsers.add_parser("analyze-status", help=argparse.SUPPRESS)
    _add_version_locator(status_parser)
    _add_project_locator(status_parser)
    status_parser.add_argument("--branch", required=True)
    status_parser.add_argument("--json", action="store_true", dest="json_output")
    status_parser.set_defaults(
        handler=handle_version_analyze_status,
        command_name="product version analyze-status",
    )

    watch_status_parser = version_subparsers.add_parser("watch-status", help=argparse.SUPPRESS)
    _add_version_locator(watch_status_parser)
    _add_project_locator(watch_status_parser)
    watch_status_parser.add_argument("--branch", required=True)
    watch_status_parser.add_argument("--json", action="store_true", dest="json_output")
    watch_status_parser.set_defaults(
        handler=handle_version_watch_status,
        command_name="product version watch-status",
    )
    _hide_subparser_choices(version_subparsers, {"analyze", "analyze-status", "watch-status"})


def _hide_subparser_choices(subparsers, hidden_names: set[str]) -> None:
    subparsers._choices_actions = [
        action for action in subparsers._choices_actions if action.dest not in hidden_names
    ]


def _add_product_locator(parser) -> None:
    parser.add_argument("--product-id", type=int)
    parser.add_argument("--product-code")


def _add_version_locator(parser) -> None:
    _add_product_locator(parser)
    parser.add_argument("--version-id", type=int)
    parser.add_argument("--version-name")


def _add_project_locator(parser, prefix: str = "") -> None:
    parser.add_argument(f"--{prefix}project-id", type=int, dest=f"{prefix.replace('-', '_')}project_id")
    parser.add_argument(f"--{prefix}project-name", dest=f"{prefix.replace('-', '_')}project_name")


def _with_db(callback):
    try:
        with closing(psycopg2.connect(get_database_url())) as conn:
            try:
                payload = callback(conn)
                conn.commit()
                return payload
            except Exception:
                conn.rollback()
                raise
    except CliError:
        raise
    except branch_analysis_service.BranchAnalysisError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except psycopg2.IntegrityError as exc:
        raise CliError(
            category="conflict",
            message="database constraint conflict",
            details={"database_error": str(exc)},
        ) from exc
    except psycopg2.Error as exc:
        raise CliError(
            category="internal_error",
            message="database operation failed",
            details={"database_error": str(exc)},
        ) from exc


def handle_product_create(args) -> dict:
    def run(conn):
        product = product_service.create_product(
            conn,
            name=args.name,
            code=args.product_code,
            description=args.description,
            owner=args.owner,
        )
        return build_success_payload(args.command_name, {"product": product})

    return _with_db(run)


def handle_product_update(args) -> dict:
    def run(conn):
        product = _resolve_product(conn, args)
        updates = {
            "name": args.name,
            "code": args.new_product_code,
            "description": args.description,
            "owner": args.owner,
            "status": args.status,
        }
        updates = {key: value for key, value in updates.items() if value is not None}
        updated = product_service.update_product(conn, product["id"], **updates)
        return build_success_payload(args.command_name, {"product": updated})

    return _with_db(run)


def handle_product_show(args) -> dict:
    def run(conn):
        product = _resolve_product(conn, args)
        versions = product_version_service.list_versions(conn, product["id"])
        projects = product_service.list_projects(conn, product["id"])
        return build_success_payload(
            args.command_name,
            {"product": product, "versions": versions, "projects": projects},
        )

    return _with_db(run)


def handle_version_create(args) -> dict:
    def run(conn):
        product = _resolve_product(conn, args)
        version = product_version_service.create_version(
            conn,
            product["id"],
            args.version_name,
            description=args.description,
            status=args.status,
            release_date=args.release_date,
        )
        return build_success_payload(args.command_name, {"product": product, "version": version})

    return _with_db(run)


def handle_version_show(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        branches = product_version_service.list_branches(conn, version["id"])
        return build_success_payload(
            args.command_name,
            {"product": product, "version": version, "branches": branches},
        )

    return _with_db(run)


def handle_version_bind_branch(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        project = _resolve_project(conn, args)
        if project.get("product_id") not in (None, product["id"]):
            raise CliError(
                category="conflict",
                message="project is already bound to another product",
                details={"project_id": project["id"], "product_id": project.get("product_id")},
            )
        if project.get("product_id") is None:
            product_service.bind_project(conn, product["id"], project["id"])
        binding = product_version_service.set_branch(
            conn,
            version["id"],
            project["id"],
            args.branch,
        )
        graph = branch_graph_repo.get_by_project_branch(conn, project["id"], args.branch)
        graph_status = "ready" if graph and graph.get("status") == "ready" else "missing"
        graph_payload = graph
        graph_action = None
        if graph_status != "ready":
            try:
                graph_payload = project_service.refresh_graph(
                    conn,
                    project_id=project["id"],
                    branch=args.branch,
                )
                graph_status = "ready"
                graph_action = "auto_refresh"
            except Exception as exc:
                graph_status = "refresh_failed"
                graph_payload = {"error": str(exc)}
        return build_success_payload(
            args.command_name,
            {
                "product": product,
                "version": version,
                "project": project,
                "binding": binding,
                "graph_status": graph_status,
                "graph_action": graph_action,
                "graph": graph_payload,
            },
        )

    return _with_db(run)


def handle_version_link_code(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        project = _resolve_project(
            conn,
            SimpleArgs(
                project_id=getattr(args, "code_project_id", None),
                project_name=getattr(args, "code_project_name", None),
            ),
        )
        link_action = "unlink" if getattr(args, "unlink", False) else "bind"
        if link_action == "unlink":
            link = product_version_service.unbind_code_link(conn, link_id=args.link_id)
            code_locator = None
        else:
            code_locator = _build_code_locator(args)
            link = product_version_service.bind_code_link(
                conn,
                product_version_id=version["id"],
                project_id=project["id"],
                doc_id=args.doc_id,
                doc_node_id=args.doc_node_id,
                relation_type=args.relation_type,
                code_locator=code_locator or {},
                source=args.source,
                confidence=args.confidence,
            )
        return build_success_payload(
            args.command_name,
            {
                "product": product,
                "version": version,
                "project": project,
                "link": link,
                "link_action": link_action,
                "link_id": getattr(args, "link_id", None),
                "code_locator": code_locator,
            },
        )

    return _with_db(run)


def _build_code_locator(args) -> dict | None:
    if getattr(args, "locator_json", None):
        try:
            locator = json.loads(args.locator_json)
        except json.JSONDecodeError as exc:
            raise CliError(
                category="validation_error",
                message="--locator-json must be a valid JSON object",
                details={"locator_json": args.locator_json},
            ) from exc
        if not isinstance(locator, dict):
            raise CliError(
                category="validation_error",
                message="--locator-json must be a valid JSON object",
                details={"locator_json": args.locator_json},
            )
        return locator
    if getattr(args, "code_node_id", None):
        return {"code_node_id": args.code_node_id}
    return None


def handle_version_code_facts(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        result = {
            "product_version_id": version["id"],
            "doc_id": args.doc_id,
            "node_types": args.node_types,
            "code_facts": [],
            "storage_status": "removed",
            "message": "code node storage has been removed; code-facts is preserved as a no-op while storage is rebuilt",
        }
        return build_success_payload(
            args.command_name,
            {"product": product, "version": version, **result},
        )

    return _with_db(run)


def handle_version_analyze(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        project = _resolve_project(conn, args)
        result = branch_analysis_service.analyze_version_branch(
            conn,
            product_version_id=version["id"],
            project_id=project["id"],
            branch=args.branch,
            force=args.force,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_version_analyze_status(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        project = _resolve_project(conn, args)
        result = branch_analysis_service.get_analysis_status(
            conn,
            product_version_id=version["id"],
            project_id=project["id"],
            branch=args.branch,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_version_watch_status(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        project = _resolve_project(conn, args)
        result = branch_analysis_service.get_analysis_status(
            conn,
            product_version_id=version["id"],
            project_id=project["id"],
            branch=args.branch,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


class SimpleArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


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
