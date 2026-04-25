from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.repositories import doc_binding_repository
from service.services import doc_scan_service


def register(subparsers) -> None:
    doc_parser = subparsers.add_parser("doc")
    doc_subparsers = doc_parser.add_subparsers(dest="doc_command", required=True)

    scan_parser = doc_subparsers.add_parser("scan")
    scan_parser.add_argument("--doc-binding-id", type=int, required=True)
    scan_parser.add_argument("--json", action="store_true", dest="json_output")
    scan_parser.set_defaults(handler=handle_doc_scan, command_name="doc scan")


def handle_doc_scan(args) -> dict:
    def run(conn):
        binding = doc_binding_repository.find_by_id(conn, args.doc_binding_id)
        if not binding:
            raise CliError(category="not_found", message="doc binding not found")
        result = doc_scan_service.scan_binding(conn, args.doc_binding_id)
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
