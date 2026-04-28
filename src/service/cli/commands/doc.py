from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.repositories import doc_binding_repository
from service.services import doc_change_service
from service.services import doc_import_service
from service.services import doc_scan_service


def register(subparsers) -> None:
    doc_parser = subparsers.add_parser("doc")
    doc_subparsers = doc_parser.add_subparsers(dest="doc_command", required=True)

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
