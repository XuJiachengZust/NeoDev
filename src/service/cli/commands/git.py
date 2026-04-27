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

    refresh_parser = git_subparsers.add_parser("post-push-refresh")
    refresh_parser.add_argument("--project-id", type=int, required=True)
    refresh_parser.add_argument("--branch", required=True)
    refresh_parser.add_argument("--version-id", type=int)
    refresh_parser.add_argument("--commit-sha")
    refresh_parser.add_argument("--json", action="store_true", dest="json_output")
    refresh_parser.set_defaults(
        handler=handle_post_push_refresh,
        command_name="git post-push-refresh",
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


def handle_post_push_refresh(args) -> dict:
    def run(conn):
        result = git_consistency_service.post_push_refresh(
            conn,
            project_id=args.project_id,
            branch=args.branch,
            version_id=args.version_id,
            commit_sha=args.commit_sha,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_dangerous_commit_list(args) -> dict:
    def run(conn):
        result = git_consistency_service.list_dangerous_commits(
            conn,
            project_id=args.project_id,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)


def handle_dangerous_commit_resolve(args) -> dict:
    def run(conn):
        result = git_consistency_service.resolve_dangerous_commit(
            conn,
            record_id=args.record_id,
            resolved_by=args.resolved_by,
        )
        return build_success_payload(args.command_name, result)

    return _with_db(run)
