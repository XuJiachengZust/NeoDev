from contextlib import closing

import psycopg2

from service.cli.errors import CliError
from service.cli.output import build_success_payload
from service.dependencies import get_database_url
from service.services import project_service


def register(subparsers) -> None:
    project_parser = subparsers.add_parser("project")
    project_subparsers = project_parser.add_subparsers(
        dest="project_command",
        required=True,
    )

    create_parser = project_subparsers.add_parser("create")
    create_parser.add_argument("--name", required=True)
    source = create_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo-url")
    source.add_argument("--repo-path")
    create_parser.add_argument("--watch-enabled", action="store_true")
    create_parser.add_argument("--neo4j-database")
    create_parser.add_argument("--neo4j-identifier")
    create_parser.add_argument("--repo-username")
    create_parser.add_argument("--repo-password")
    create_parser.add_argument("--json", action="store_true", dest="json_output")
    create_parser.set_defaults(handler=handle_project_create, command_name="project create")

    show_parser = project_subparsers.add_parser("show")
    locator = show_parser.add_mutually_exclusive_group(required=True)
    locator.add_argument("--project-id", type=int)
    locator.add_argument("--project-name")
    show_parser.add_argument("--json", action="store_true", dest="json_output")
    show_parser.set_defaults(handler=handle_project_show, command_name="project show")


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


def handle_project_create(args) -> dict:
    def run(conn):
        repo_path = args.repo_url or args.repo_path
        project = project_service.create_project(
            conn,
            name=args.name,
            repo_path=repo_path,
            watch_enabled=args.watch_enabled,
            neo4j_database=args.neo4j_database,
            neo4j_identifier=args.neo4j_identifier,
            repo_username=args.repo_username,
            repo_password=args.repo_password,
            repo_url=args.repo_url,
        )
        return build_success_payload(
            args.command_name,
            {
                "project": project,
                "auto_graph_analysis": True,
                "message": "仓库已登记，远程 NeoDev 已自动触发图谱构建。",
            },
        )

    return _with_db(run)


def handle_project_show(args) -> dict:
    def run(conn):
        project = _resolve_project(conn, args)
        return build_success_payload(args.command_name, {"project": project})

    return _with_db(run)


def _resolve_project(conn, args) -> dict:
    if args.project_id is not None:
        project = project_service.get_project(conn, args.project_id)
        if not project:
            raise CliError(category="not_found", message="project not found")
        return project
    matches = project_service.find_projects_by_name(conn, args.project_name)
    if not matches:
        raise CliError(category="not_found", message="project not found")
    if len(matches) > 1:
        raise CliError(
            category="conflict",
            message="project name is ambiguous",
            details={"project_name": args.project_name, "matches": [row["id"] for row in matches]},
        )
    return matches[0]
