from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.services import git_consistency_service


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


def _with_db(callback):
    try:
        with closing(psycopg2.connect(get_database_url())) as conn:
            result = callback(conn)
            conn.commit()
            return result
    except CliError:
        raise
    except git_consistency_service.GitConsistencyError as exc:
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
