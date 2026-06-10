from contextlib import closing
import json
from pathlib import Path

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.services import git_consistency_service
from service.services import post_push_update_service


def register(subparsers) -> None:
    git_parser = subparsers.add_parser("git")
    git_subparsers = git_parser.add_subparsers(dest="git_command", required=True)

    verify_parser = git_subparsers.add_parser("verify-doc-change")
    verify_parser.add_argument("--project-id", type=int, required=True)
    verify_parser.add_argument("--branch", required=True)
    verify_parser.add_argument("--commit-sha", required=True)
    verify_parser.add_argument("--commit-message", required=True)
    verify_parser.add_argument("--json", action="store_true", dest="json_output")
    verify_parser.set_defaults(
        handler=handle_verify_doc_change,
        command_name="git verify-doc-change",
    )

    post_push_parser = git_subparsers.add_parser("post-push-graph-update")
    post_push_parser.add_argument("--payload-file")
    post_push_parser.add_argument("--payload-json")
    post_push_parser.add_argument("--json", action="store_true", dest="json_output")
    post_push_parser.set_defaults(
        handler=handle_post_push_graph_update,
        command_name="git post-push-graph-update",
    )

    dangerous_parser = git_subparsers.add_parser("dangerous-commit")
    dangerous_subparsers = dangerous_parser.add_subparsers(
        dest="dangerous_command",
        required=True,
    )

    list_parser = dangerous_subparsers.add_parser("list")
    list_parser.add_argument("--project-id", type=int)
    list_parser.add_argument("--json", action="store_true", dest="json_output")
    list_parser.set_defaults(
        handler=handle_dangerous_commit_list,
        command_name="git dangerous-commit list",
    )

    resolve_parser = dangerous_subparsers.add_parser("resolve")
    resolve_parser.add_argument("--record-id", type=int, required=True)
    resolve_parser.add_argument("--resolved-by", required=True)
    resolve_parser.add_argument("--json", action="store_true", dest="json_output")
    resolve_parser.set_defaults(
        handler=handle_dangerous_commit_resolve,
        command_name="git dangerous-commit resolve",
    )


def _with_db(callback):
    try:
        with closing(psycopg2.connect(get_database_url())) as conn:
            try:
                result = callback(conn)
            except git_consistency_service.GitConsistencyError as exc:
                conn.commit()
                raise CliError(
                    category=exc.category,
                    message=exc.message,
                    details=exc.details,
                ) from exc
            conn.commit()
            return result
    except CliError:
        raise
    except psycopg2.Error as exc:
        raise CliError(
            category="internal_error",
            message="database operation failed",
            details={"database_error": str(exc)},
        ) from exc


def handle_verify_doc_change(args) -> dict:
    def run(conn):
        result = git_consistency_service.verify_doc_change(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            commit_sha=args.commit_sha,
            commit_message=args.commit_message,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_post_push_graph_update(args) -> dict:
    payload = _load_post_push_payload(args)
    try:
        conn = psycopg2.connect(get_database_url())
    except psycopg2.Error as exc:
        raise CliError(
            category="internal_error",
            message="database connection failed",
            details={"database_error": str(exc), "rollback_status": "not_needed"},
        ) from exc
    try:
        with closing(conn):
            result = post_push_update_service.apply_post_push_update(conn, payload)
            return build_success_payload(args.command_name, result)
    except post_push_update_service.PostPushUpdateError as exc:
        raise CliError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc
    except CliError:
        raise
    except psycopg2.Error as exc:
        raise CliError(
            category="internal_error",
            message="database operation failed",
            details={"database_error": str(exc), "rollback_status": "rollback_failed"},
        ) from exc


def handle_dangerous_commit_list(args) -> dict:
    def run(conn):
        result = git_consistency_service.list_dangerous_commits(
            conn,
            project_id=args.project_id,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def _load_post_push_payload(args) -> dict:
    if bool(args.payload_file) == bool(args.payload_json):
        raise CliError(
            category="invalid_argument",
            message="provide exactly one of --payload-file or --payload-json",
            details={"rollback_status": "not_needed"},
        )
    try:
        if args.payload_file:
            return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
        return json.loads(args.payload_json)
    except OSError as exc:
        raise CliError(
            category="invalid_argument",
            message="payload file is not readable",
            details={"payload_file": args.payload_file, "error": str(exc), "rollback_status": "not_needed"},
        ) from exc
    except json.JSONDecodeError as exc:
        raise CliError(
            category="invalid_argument",
            message="payload must be valid JSON",
            details={"error": str(exc), "rollback_status": "not_needed"},
        ) from exc


def handle_dangerous_commit_resolve(args) -> dict:
    def run(conn):
        result = git_consistency_service.resolve_dangerous_commit(
            conn,
            record_id=args.record_id,
            resolved_by=args.resolved_by,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)
