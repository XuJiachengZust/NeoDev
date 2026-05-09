from contextlib import closing
import os
import re

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.repositories import doc_binding_repository
from service.repositories import product_repository
from service.repositories import project_repository
from service.services import product_version_service
from service.services import doc_change_service
from service.services import doc_graph_service
from service.services import doc_import_service
from service.services import doc_scan_service


def register(subparsers) -> None:
    doc_parser = subparsers.add_parser("doc")
    doc_subparsers = doc_parser.add_subparsers(dest="doc_command", required=True)

    binding_parser = doc_subparsers.add_parser("binding")
    binding_subparsers = binding_parser.add_subparsers(
        dest="binding_command",
        required=True,
    )

    binding_create_parser = binding_subparsers.add_parser("create")
    _add_product_locator(binding_create_parser)
    version_source = binding_create_parser.add_mutually_exclusive_group()
    version_source.add_argument("--version-id", type=int)
    version_source.add_argument("--version-name")
    project_source = binding_create_parser.add_mutually_exclusive_group()
    project_source.add_argument("--project-id", type=int)
    project_source.add_argument("--project-name")
    binding_create_parser.add_argument("--repo-url")
    binding_create_parser.add_argument("--repo-path")
    binding_create_parser.add_argument("--branch", default="main")
    binding_create_parser.add_argument("--json", action="store_true", dest="json_output")
    binding_create_parser.set_defaults(
        handler=handle_doc_binding_create,
        command_name="doc binding create",
    )

    binding_list_parser = binding_subparsers.add_parser("list")
    _add_product_locator(binding_list_parser)
    binding_list_parser.add_argument("--json", action="store_true", dest="json_output")
    binding_list_parser.set_defaults(
        handler=handle_doc_binding_list,
        command_name="doc binding list",
    )

    graph_parser = doc_subparsers.add_parser("graph")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)
    graph_show_parser = graph_subparsers.add_parser("show")
    graph_show_parser.add_argument("--product-name", required=True)
    graph_show_parser.add_argument("--version-name", required=True)
    graph_show_parser.add_argument("--json", action="store_true", dest="json_output")
    graph_show_parser.set_defaults(
        handler=handle_doc_graph_show,
        command_name="doc graph show",
    )

    scan_parser = doc_subparsers.add_parser("scan")
    scan_parser.add_argument("--doc-binding-id", type=int, required=True)
    scan_parser.add_argument("--json", action="store_true", dest="json_output")
    scan_parser.set_defaults(handler=handle_doc_scan, command_name="doc scan")

    import_parser = doc_subparsers.add_parser("import")
    import_parser.add_argument("--doc-binding-id", type=int, required=True)
    import_parser.add_argument("--force", action="store_true")
    import_parser.add_argument("--json", action="store_true", dest="json_output")
    import_parser.set_defaults(handler=handle_doc_import, command_name="doc import")

    change_parser = doc_subparsers.add_parser("change")
    change_subparsers = change_parser.add_subparsers(dest="change_command", required=True)

    register_parser = change_subparsers.add_parser("register")
    register_parser.add_argument("--document-id", type=int, required=True)
    register_parser.add_argument("--doc-change-id")
    register_parser.add_argument("--source-commit")
    register_parser.add_argument("--summary")
    register_parser.add_argument("--created-by")
    register_parser.add_argument("--json", action="store_true", dest="json_output")
    register_parser.set_defaults(
        handler=handle_doc_change_register,
        command_name="doc change register",
    )

    show_parser = change_subparsers.add_parser("show")
    _add_doc_change_locator(show_parser)
    show_parser.add_argument("--json", action="store_true", dest="json_output")
    show_parser.set_defaults(
        handler=handle_doc_change_show,
        command_name="doc change show",
    )

    implemented_parser = change_subparsers.add_parser("mark-implemented")
    _add_doc_change_locator(implemented_parser)
    implemented_parser.add_argument("--json", action="store_true", dest="json_output")
    implemented_parser.set_defaults(
        handler=handle_doc_change_mark_implemented,
        command_name="doc change mark-implemented",
    )


def _add_doc_change_locator(parser) -> None:
    parser.add_argument("--change-id", type=int)
    parser.add_argument("--doc-change-id")


def _add_product_locator(parser) -> None:
    locator = parser.add_mutually_exclusive_group(required=True)
    locator.add_argument("--product-id", type=int)
    locator.add_argument("--product-code")


def handle_doc_binding_create(args) -> dict:
    def run(conn):
        product = _resolve_product(conn, args)
        version = _resolve_version(conn, product, args)
        if not version:
            raise CliError(
                category="invalid_argument",
                message="doc binding must be scoped to a product version",
            )
        project = _resolve_project(conn, args)
        source_repo_url = _first_text(
            args.repo_url,
            (project or {}).get("repo_url"),
            _remote_url_or_empty((project or {}).get("repo_path")),
        )
        source_repo_path = _first_text(
            args.repo_path,
            _local_path_or_empty((project or {}).get("repo_path")),
        )
        if not source_repo_url and not source_repo_path:
            raise CliError(
                category="invalid_argument",
                message="provide --repo-url, --repo-path, --project-id, or --project-name",
            )
        repo_path = source_repo_path or _default_doc_repo_path(product, project, source_repo_url)
        binding = doc_binding_repository.create(
            conn,
            product_id=product["id"],
            product_version_id=(version or {}).get("id"),
            repo_path=repo_path,
            repo_url=source_repo_url,
            default_branch=args.branch,
            is_active=True,
        )
        return build_success_payload(
            args.command_name,
            {
                "product": product,
                "version": version,
                "project": project,
                "binding": binding,
                "import_command": f"neodev doc import --doc-binding-id {binding['id']} --json",
            },
        )

    return _with_db(run)


def handle_doc_graph_show(args) -> dict:
    result = doc_graph_service.document_graph_summary(
        product_name=args.product_name,
        version_name=args.version_name,
    )
    return build_success_payload(args.command_name, result)


def handle_doc_binding_list(args) -> dict:
    def run(conn):
        product = _resolve_product(conn, args)
        bindings = doc_binding_repository.list_active_by_product(conn, product["id"])
        return build_success_payload(
            args.command_name,
            {
                "product": product,
                "bindings": bindings,
            },
        )

    return _with_db(run)


def handle_doc_scan(args) -> dict:
    def run(conn):
        binding = doc_binding_repository.find_by_id(conn, args.doc_binding_id)
        if not binding:
            raise CliError(category="not_found", message="doc binding not found")
        result = doc_scan_service.scan_binding(conn, args.doc_binding_id)
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_doc_import(args) -> dict:
    def run(conn):
        binding = doc_binding_repository.find_by_id(conn, args.doc_binding_id)
        if not binding:
            raise CliError(category="not_found", message="doc binding not found")
        result = doc_import_service.import_binding(
            conn,
            args.doc_binding_id,
            force=args.force,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_doc_change_register(args) -> dict:
    def run(conn):
        result = doc_change_service.register_doc_change(
            conn,
            document_id=args.document_id,
            doc_change_id=args.doc_change_id,
            source_commit=args.source_commit,
            summary=args.summary,
            created_by=args.created_by,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_doc_change_show(args) -> dict:
    def run(conn):
        result = doc_change_service.show_doc_change(
            conn,
            change_id=args.change_id,
            doc_change_id=args.doc_change_id,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_doc_change_mark_implemented(args) -> dict:
    def run(conn):
        result = doc_change_service.mark_implemented(
            conn,
            change_id=args.change_id,
            doc_change_id=args.doc_change_id,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


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
    except psycopg2.IntegrityError as exc:
        raise CliError(
            category="name_conflict",
            message="database constraint conflict",
            details={"database_error": str(exc)},
        ) from exc
    except psycopg2.Error as exc:
        raise CliError(
            category="internal_error",
            message="database operation failed",
            details={"database_error": str(exc)},
        ) from exc


def _resolve_product(conn, args) -> dict:
    if args.product_id is not None:
        product = product_repository.find_by_id(conn, args.product_id)
    else:
        product = product_repository.find_by_code(conn, args.product_code)
    if not product:
        raise CliError(category="not_found", message="product not found")
    return product


def _resolve_project(conn, args) -> dict | None:
    if getattr(args, "project_id", None) is not None:
        project = project_repository.find_by_id(conn, args.project_id)
        if not project:
            raise CliError(category="not_found", message="project not found")
        return project
    project_name = getattr(args, "project_name", None)
    if not project_name:
        return None
    matches = project_repository.find_by_name(conn, project_name)
    if not matches:
        raise CliError(category="not_found", message="project not found")
    return max(matches, key=lambda row: row["id"])


def _resolve_version(conn, product: dict, args) -> dict | None:
    version_id = getattr(args, "version_id", None)
    version_name = getattr(args, "version_name", None)
    if version_id is None and not version_name:
        return None
    if version_id is not None:
        version = product_version_service.get_version(conn, version_id)
        if not version or version["product_id"] != product["id"]:
            raise CliError(
                category="not_found",
                message="product version not found",
                details={"version_id": version_id, "product_id": product["id"]},
            )
        return version
    version = product_version_service.get_version_by_name(conn, product["id"], version_name)
    if not version:
        raise CliError(
            category="not_found",
            message="product version not found",
            details={"version_name": version_name, "product_id": product["id"]},
        )
    return version


def _first_text(*values: str | None) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _is_remote_url(value: str | None) -> bool:
    text = str(value or "").strip()
    return (
        text.startswith("http://")
        or text.startswith("https://")
        or text.startswith("git@")
        or ("://" in text and not os.path.isdir(text))
    )


def _remote_url_or_empty(value: str | None) -> str:
    text = str(value or "").strip()
    return text if _is_remote_url(text) else ""


def _local_path_or_empty(value: str | None) -> str:
    text = str(value or "").strip()
    return "" if _is_remote_url(text) else text


def _default_doc_repo_path(product: dict, project: dict | None, repo_url: str) -> str:
    base = (
        os.environ.get("REQUIREMENT_DOCS_ROOT")
        or os.environ.get("REPO_CLONE_BASE")
        or "/data/requirement_docs"
    )
    name_source = (project or {}).get("name") or product.get("code") or repo_url or "docs"
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(name_source)).strip(".-").lower()
    if not name:
        name = "docs"
    return os.path.join(base, name)
