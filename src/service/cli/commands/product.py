import argparse
import json
from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.help_visibility import hide_subparser_choices
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.repositories import branch_graph_repository as branch_graph_repo
from service.services import branch_analysis_service
from service.services import branch_graph_neo4j_service
from service.services import neo4j_config_service
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
        metavar="{create,show,bind-branch,unbind-branch,link-code,code-facts}",
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
    _add_version_show_locator(version_show_parser)
    version_show_parser.add_argument("--project-name")
    version_show_parser.add_argument("--branch-name")
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

    unbind_parser = version_subparsers.add_parser("unbind-branch")
    _add_version_locator(unbind_parser)
    _add_project_locator(unbind_parser)
    unbind_parser.add_argument("--json", action="store_true", dest="json_output")
    unbind_parser.set_defaults(
        handler=handle_version_unbind_branch,
        command_name="product version unbind-branch",
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
    hide_subparser_choices(version_subparsers, {"analyze", "analyze-status", "watch-status"})


def _add_product_locator(parser) -> None:
    parser.add_argument("--product-id", type=int)
    parser.add_argument("--product-code")
    parser.add_argument("--product-name")


def _add_version_locator(parser) -> None:
    _add_product_locator(parser)
    parser.add_argument("--version-id", type=int)
    parser.add_argument("--version-name")


def _add_version_show_locator(parser) -> None:
    _add_product_locator(parser)
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
    except product_version_service.ProductVersionError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except psycopg2.IntegrityError as exc:
        raise CliError(
            category=_integrity_error_category(exc),
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
        if getattr(args, "project_name", None) or getattr(args, "branch_name", None):
            if getattr(args, "version_name", None):
                raise CliError(
                    category="invalid_argument",
                    message="do not combine --version-name with --project-name/--branch-name",
                )
            return build_success_payload(args.command_name, _show_versions_by_branch(conn, args))
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        branches = product_version_service.list_branches(conn, version["id"])
        return build_success_payload(
            args.command_name,
            _version_show_payload(product, version, branches),
        )

    return _with_db(run)


def _show_versions_by_branch(conn, args) -> dict:
    if not getattr(args, "project_name", None) or not getattr(args, "branch_name", None):
        raise CliError(
            category="invalid_argument",
            message="provide both --project-name and --branch-name for branch lookup",
        )
    project = _resolve_project(conn, SimpleArgs(project_name=args.project_name, project_id=None))
    product_filter = None
    if _has_product_locator(args):
        product_filter = _resolve_product(
            conn,
            SimpleArgs(
                product_id=getattr(args, "product_id", None),
                product_code=getattr(args, "product_code", None),
                product_name=getattr(args, "product_name", None),
            ),
        )
    rows = product_version_service.list_versions_by_project_branch(
        conn,
        project_id=project["id"],
        branch_name=args.branch_name,
    )
    if product_filter is not None:
        rows = [row for row in rows if row["product_id"] == product_filter["id"]]
    resolved_versions = []
    for row in rows:
        product = {
            "id": row["product_id"],
            "name": row["product_name"],
            "code": row["product_code"],
        }
        version = {
            "id": row["id"],
            "product_id": row["product_id"],
            "version_name": row["version_name"],
            "description": row.get("description"),
            "status": row.get("status"),
            "release_date": row.get("release_date"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        branch = {
            "id": row["branch_binding_id"],
            "product_version_id": row["id"],
            "project_id": project["id"],
            "project_name": project["name"],
            "branch_name": row["branch_name"],
            "branch": row["branch_name"],
        }
        resolved_versions.append(
            {
                "product": product,
                "version": version,
                "branch": branch,
                "query_params": _query_params(product, version, branch),
            }
        )
    return {
        "project": project,
        "branch_name": args.branch_name,
        "resolved_versions": resolved_versions,
    }


def _has_product_locator(args) -> bool:
    return any(
        getattr(args, name, None) not in (None, "")
        for name in ("product_id", "product_code", "product_name")
    )


def _integrity_error_category(exc: psycopg2.IntegrityError) -> str:
    constraint = str(getattr(getattr(exc, "diag", None), "constraint_name", "") or "")
    message = str(exc)
    name_constraints = (
        "uq_products_name",
        "uq_projects_name",
        "uq_product_versions_product_name",
        "product_versions_product_id_version_name_key",
        "uq_pvb_project_branch",
        "product_version_branches_product_version_id_project_id_key",
    )
    if any(name in constraint or name in message for name in name_constraints):
        return "name_conflict"
    return "conflict"


def _version_show_payload(product: dict, version: dict, branches: list[dict]) -> dict:
    return {
        "product": product,
        "version": version,
        "branches": branches,
        "query_params": [_query_params(product, version, branch) for branch in branches],
    }


def _query_params(product: dict, version: dict, branch: dict) -> dict:
    return {
        "product_name": product.get("name"),
        "version_name": version.get("version_name"),
        "project_name": branch.get("project_name"),
        "branch_name": branch.get("branch_name") or branch.get("branch"),
    }


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
                "mutation_action": "bind",
                "mutation_target": "branch",
                "mutation_status": graph_status,
                "graph_status": graph_status,
                "graph_action": graph_action,
                "graph": graph_payload,
            },
        )

    return _with_db(run)


def handle_version_unbind_branch(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        project = _resolve_project(conn, args)
        branches = product_version_service.list_branches(conn, version["id"])
        binding = next((row for row in branches if int(row["project_id"]) == int(project["id"])), None)
        if not binding:
            raise CliError(
                category="not_found",
                message="branch mapping not found",
                details={"product_version_id": version["id"], "project_id": project["id"]},
            )
        removed = product_version_service.remove_branch(conn, version["id"], project["id"])
        if not removed:
            raise CliError(
                category="not_found",
                message="branch mapping not found",
                details={"product_version_id": version["id"], "project_id": project["id"]},
            )
        graph = branch_graph_repo.get_by_project_branch(conn, project["id"], binding["branch_name"])
        graph_status = "ready" if graph and graph.get("status") == "ready" else "missing"
        return build_success_payload(
            args.command_name,
            {
                "product": product,
                "version": version,
                "project": project,
                "binding": binding,
                "binding_removed": True,
                "mutation_action": "unbind",
                "mutation_target": "branch",
                "mutation_status": "removed",
                "graph_status": graph_status,
                "graph_action": None,
                "graph": graph,
            },
        )

    return _with_db(run)


def handle_version_link_code(args) -> dict:
    def run(conn):
        version = _resolve_version(conn, args)
        product = product_service.get_product(conn, version["product_id"])
        link_action = "unlink" if getattr(args, "unlink", False) else "bind"
        if link_action == "unlink":
            if not getattr(args, "link_id", None):
                raise CliError(category="invalid_argument", message="--link-id is required for unlink")
            link = product_version_service.unbind_code_link(
                conn,
                link_id=args.link_id,
                product_version_id=version["id"],
            )
            if not link:
                raise CliError(
                    category="not_found",
                    message="active code link not found",
                    details={"link_id": args.link_id, "product_version_id": version["id"]},
                )
            project = project_service.get_project(conn, link["project_id"])
            if not project:
                raise CliError(category="not_found", message="project not found")
            neo4j_link = _delete_neo4j_doc_code_link(project=project, link=link)
            code_locator = None
            branch_mapping = {
                "project_id": link["project_id"],
                "branch_name": link["branch_name"],
                "branch": link["branch_name"],
            }
            graph = branch_graph_repo.get_by_project_branch(conn, link["project_id"], link["branch_name"])
            graph_status = "ready" if graph and graph.get("status") == "ready" else "missing"
            graph_action = None
        else:
            project = _resolve_project(
                conn,
                SimpleArgs(
                    project_id=getattr(args, "code_project_id", None),
                    project_name=getattr(args, "code_project_name", None),
                ),
            )
            if not getattr(args, "doc_id", None):
                raise CliError(category="invalid_argument", message="--doc-id is required for link-code")
            code_locator = _build_code_locator(args)
            code_node_id = (code_locator or {}).get("code_node_id")
            if not code_node_id:
                raise CliError(
                    category="invalid_argument",
                    message="provide --code-node-id or --locator-json with code_node_id",
                )
            branch_mapping = product_version_service.get_bound_branch(
                conn,
                product_version_id=version["id"],
                project_id=project["id"],
            )
            graph, graph_status, graph_action = _ensure_ready_branch_graph(
                conn,
                project=project,
                branch=branch_mapping["branch_name"],
            )
            neo4j_config, neo4j_database = _load_neo4j_config(project)
            if not branch_graph_neo4j_service.code_node_exists(
                config=neo4j_config,
                database=neo4j_database,
                project_id=project["id"],
                branch_name=branch_mapping["branch_name"],
                code_node_id=code_node_id,
            ):
                raise CliError(
                    category="not_found",
                    message="code node not found in branch graph",
                    details={
                        "project_id": project["id"],
                        "branch": branch_mapping["branch_name"],
                        "code_node_id": code_node_id,
                    },
                )
            link = product_version_service.bind_code_link(
                conn,
                product_version_id=version["id"],
                project_id=project["id"],
                doc_id=args.doc_id,
                doc_node_id=args.doc_node_id,
                relation_type=args.relation_type or "LINKS_TO_CODE",
                code_locator=code_locator or {},
                source=args.source,
                confidence=args.confidence,
            )
            neo4j_link = branch_graph_neo4j_service.upsert_doc_code_link(
                config=neo4j_config,
                database=neo4j_database,
                project_id=project["id"],
                branch_name=branch_mapping["branch_name"],
                graph_id=graph["id"],
                link=link,
                version_scope={
                    "product_version_id": version["id"],
                    "product_name": product.get("name"),
                    "version_name": version.get("version_name"),
                    "project_name": project.get("name"),
                },
            )
            if neo4j_link.get("status") != "linked":
                raise CliError(
                    category="not_found",
                    message="code link could not be projected to Neo4j",
                    details={"neo4j_link": neo4j_link},
                )
        return build_success_payload(
            args.command_name,
            {
                "product": product,
                "version": version,
                "project": project,
                "branch": branch_mapping,
                "graph": graph,
                "graph_status": graph_status,
                "graph_action": graph_action,
                "link": link,
                "link_action": link_action,
                "neo4j_link": neo4j_link,
                "mutation_action": link_action,
                "mutation_target": "code_link",
                "mutation_status": (link or {}).get("status") if link else "unknown",
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
        branches = product_version_service.list_branches(conn, version["id"])
        facts = []
        degraded_reasons = []
        for branch in branches:
            project = project_service.get_project(conn, branch["project_id"])
            graph = branch_graph_repo.get_by_project_branch(conn, branch["project_id"], branch["branch_name"])
            if not graph or graph.get("status") != "ready":
                degraded_reasons.append(
                    {
                        "project_id": branch["project_id"],
                        "branch": branch["branch_name"],
                        "reason": "branch_graph_not_ready",
                    }
                )
                continue
            try:
                neo4j_config, neo4j_database = _load_neo4j_config(project)
                branch_facts = branch_graph_neo4j_service.list_doc_code_facts(
                    config=neo4j_config,
                    database=neo4j_database,
                    project_id=branch["project_id"],
                    branch_name=branch["branch_name"],
                    doc_id=args.doc_id,
                    node_types=args.node_types,
                )
            except CliError as exc:
                degraded_reasons.append(
                    {
                        "project_id": branch["project_id"],
                        "branch": branch["branch_name"],
                        "reason": exc.category,
                    }
                )
                continue
            for fact in branch_facts:
                fact["project_id"] = branch["project_id"]
                fact["project_name"] = branch.get("project_name")
                fact["branch"] = branch["branch_name"]
                facts.append(fact)
        result = {
            "product_version_id": version["id"],
            "doc_id": args.doc_id,
            "node_types": args.node_types,
            "code_facts": facts,
            "storage_status": "neo4j",
            "degraded_reasons": degraded_reasons,
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


def _ensure_ready_branch_graph(conn, *, project: dict, branch: str) -> tuple[dict, str, str | None]:
    graph = branch_graph_repo.get_by_project_branch(conn, project["id"], branch)
    if graph and graph.get("status") == "ready":
        return graph, "ready", None
    project_service.refresh_graph(conn, project_id=project["id"], branch=branch)
    graph = branch_graph_repo.get_by_project_branch(conn, project["id"], branch)
    if not graph or graph.get("status") != "ready":
        raise CliError(
            category="refresh_failed",
            message="branch graph is not ready after refresh",
            details={"project_id": project["id"], "branch": branch, "graph": graph},
        )
    return graph, "ready", "auto_refresh"


def _load_neo4j_config(project: dict) -> tuple[dict, str | None]:
    neo4j_config, neo4j_database = neo4j_config_service.load_neo4j_config(project)
    if not neo4j_config:
        raise CliError(
            category="invalid_config",
            message="Neo4j is not configured",
            details={"project_id": project.get("id")},
        )
    return neo4j_config, neo4j_database


def _delete_neo4j_doc_code_link(*, project: dict, link: dict) -> dict:
    neo4j_config, neo4j_database = _load_neo4j_config(project)
    return branch_graph_neo4j_service.delete_doc_code_link(
        config=neo4j_config,
        database=neo4j_database,
        link_id=link["id"],
    )


def _resolve_product(conn, args) -> dict:
    product_id = getattr(args, "product_id", None)
    product_code = getattr(args, "product_code", None)
    product_name = getattr(args, "product_name", None)
    provided = [value is not None and value != "" for value in (product_id, product_code, product_name)]
    if not any(provided):
        raise CliError(
            category="invalid_argument",
            message="provide --product-id, --product-code, or --product-name",
        )
    if sum(1 for item in provided if item) > 1:
        raise CliError(
            category="invalid_argument",
            message="provide only one product locator",
        )
    if product_id is not None:
        product = product_service.get_product(conn, product_id)
    elif product_name:
        matches = product_service.find_products_by_name(conn, product_name)
        if len(matches) > 1:
            raise CliError(
                category="ambiguous_name",
                message="product name is ambiguous",
                details={"product_name": product_name, "matches": [row["id"] for row in matches]},
            )
        product = matches[0] if matches else None
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
            category="ambiguous_name",
            message="project name is ambiguous",
            details={"project_name": project_name, "matches": [row["id"] for row in matches]},
        )
    return matches[0]
