from service.cli.output import build_success_payload
from service.cli.workflow_runner import WorkflowStepSpec, run_workflow


def register(subparsers) -> None:
    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")
    doctor_parser.set_defaults(
        handler=handle_doctor,
        command_name="doctor",
        scenario_id="S01",
        stage="context",
    )

    context_parser = subparsers.add_parser("context")
    context_subparsers = context_parser.add_subparsers(dest="context_command", required=True)
    show_parser = context_subparsers.add_parser("show")
    show_parser.add_argument("--json", action="store_true", dest="json_output")
    show_parser.set_defaults(
        handler=handle_context_show,
        command_name="context show",
        scenario_id="S06",
        stage="context",
    )

    setup_parser = subparsers.add_parser("setup")
    setup_subparsers = setup_parser.add_subparsers(dest="setup_command", required=True)
    repo_parser = setup_subparsers.add_parser("repo")
    repo_parser.add_argument("--json", action="store_true", dest="json_output")
    repo_parser.set_defaults(
        handler=handle_setup_repo,
        command_name="setup repo",
        scenario_id="S01",
        stage="setup",
    )

    docs_parser = subparsers.add_parser("docs")
    docs_subparsers = docs_parser.add_subparsers(dest="docs_command", required=True)
    sync_parser = docs_subparsers.add_parser("sync")
    sync_parser.add_argument("--json", action="store_true", dest="json_output")
    sync_parser.set_defaults(
        handler=handle_docs_sync,
        command_name="docs sync",
        scenario_id="S02",
        stage="docs",
    )

    change_parser = subparsers.add_parser("change")
    change_subparsers = change_parser.add_subparsers(dest="change_command", required=True)
    start_parser = change_subparsers.add_parser("start")
    start_parser.add_argument("--json", action="store_true", dest="json_output")
    start_parser.set_defaults(
        handler=handle_change_start,
        command_name="change start",
        scenario_id="S03",
        stage="change",
    )
    impact_parser = change_subparsers.add_parser("impact")
    impact_parser.add_argument("--json", action="store_true", dest="json_output")
    impact_parser.set_defaults(
        handler=handle_change_impact,
        command_name="change impact",
        scenario_id="S04",
        stage="impact",
    )

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--json", action="store_true", dest="json_output")
    status_parser.set_defaults(
        handler=handle_status,
        command_name="status",
        scenario_id="S05",
        stage="status",
    )


def _workflow_payload(*, scenario_id: str, stage: str, summary: dict, next_actions: list[dict]) -> dict:
    return run_workflow(
        scenario_id=scenario_id,
        stage=stage,
        steps=_steps_for(stage),
        summary=summary,
        closure_evidence=[{"type": stage, "status": "not_evaluated"}],
        next_actions=next_actions,
    )


def _steps_for(stage: str) -> list[WorkflowStepSpec]:
    return {
        "context": [
            WorkflowStepSpec("check_environment", "python plugins/neodev-rd-knowledge/check_neodev_environment.py", "Check local NeoDev environment."),
            WorkflowStepSpec("show_config", "neodev config show", "Read configured remote service."),
            WorkflowStepSpec("version_check", "neodev cli version-check --json", "Check CLI/plugin compatibility."),
        ],
        "setup": [
            WorkflowStepSpec("resolve_repository", "git remote -v", "Read repository remotes and branch."),
            WorkflowStepSpec("bind_branch", "neodev product version bind-branch --json", "Bind product version to project branch."),
            WorkflowStepSpec("initialize_graph", "neodev project refresh-graph --json", "Initialize or refresh branch graph."),
        ],
        "docs": [
            WorkflowStepSpec("validate_mvp_docs", "python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>", "Validate controlled document front matter.", retry_hint="Fix document metadata and rerun `neodev docs sync`."),
            WorkflowStepSpec("validate_obsidian_docs", "python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>", "Validate Obsidian links and related documents.", retry_hint="Fix document links and rerun `neodev docs sync`."),
            WorkflowStepSpec("sync_binding", "neodev doc binding list/create --json", "Resolve version-scoped document binding."),
            WorkflowStepSpec("scan_docs", "neodev doc scan --json", "Scan controlled documents."),
            WorkflowStepSpec("import_docs", "neodev doc import --json", "Import controlled documents."),
        ],
        "change": [
            WorkflowStepSpec("ensure_docs_synced", "neodev docs sync --json", "Ensure controlled documents are imported."),
            WorkflowStepSpec("register_doc_change", "neodev doc change register --json", "Register document-backed change."),
        ],
        "impact": [
            WorkflowStepSpec("load_doc_change", "neodev doc change show --json", "Load DocChange context."),
            WorkflowStepSpec("graph_impact", "neodev graph impact --json", "Read document-to-code impact."),
            WorkflowStepSpec("read_code_context", "neodev graph get-chain/entity-context --json", "Read affected code graph context."),
        ],
        "status": [
            WorkflowStepSpec("show_context", "neodev context show --json", "Read active product/version/project/branch context."),
            WorkflowStepSpec("show_doc_graph", "neodev doc graph show --json", "Read document graph status."),
            WorkflowStepSpec("inspect_hook_result", "post-push hook run record", "Interpret post-push hook result."),
            WorkflowStepSpec("summarize_gaps", "neodev status --json", "Summarize remaining closure gaps."),
        ],
    }.get(stage, [])


def _build(args, *, summary: dict, next_actions: list[dict]) -> dict:
    return build_success_payload(
        args.command_name,
        _workflow_payload(
            scenario_id=args.scenario_id,
            stage=args.stage,
            summary=summary,
            next_actions=next_actions,
        ),
    )


def handle_doctor(args) -> dict:
    return _build(
        args,
        summary={"server_ok": None, "compatibility": "not_checked"},
        next_actions=[{"intent": "context", "command": "neodev context show"}],
    )


def handle_context_show(args) -> dict:
    return _build(
        args,
        summary={"context_status": "not_resolved"},
        next_actions=[{"intent": "context", "command": "neodev setup repo"}],
    )


def handle_setup_repo(args) -> dict:
    return _build(
        args,
        summary={"repo_binding": {"status": "not_started"}},
        next_actions=[{"intent": "docs", "command": "neodev docs sync"}],
    )


def handle_docs_sync(args) -> dict:
    return _build(
        args,
        summary={"doc_graph_status": "not_started", "imported_docs": 0, "failed_docs": []},
        next_actions=[{"intent": "change", "command": "neodev change start"}],
    )


def handle_change_start(args) -> dict:
    return _build(
        args,
        summary={"doc_change_id": None, "linked_docs": []},
        next_actions=[{"intent": "change", "command": "neodev change impact"}],
    )


def handle_change_impact(args) -> dict:
    return _build(
        args,
        summary={"impacted_nodes": [], "risk_points": []},
        next_actions=[{"intent": "submit", "command": "neodev git check"}],
    )


def handle_status(args) -> dict:
    return _build(
        args,
        summary={"hook_status": "unknown", "open_gaps": []},
        next_actions=[{"intent": "done", "command": None}],
    )
