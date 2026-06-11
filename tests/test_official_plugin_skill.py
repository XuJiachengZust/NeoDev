import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "neodev-rd-knowledge"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def test_official_plugin_manifest_and_marketplace_are_registered():
    manifest = _read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")

    assert manifest["name"] == "neodev-rd-knowledge"
    assert manifest["version"] == "0.2.0"
    assert manifest["skills"] == "./skills/"
    assert "neodev" in manifest["keywords"]
    assert len(manifest["interface"]["defaultPrompt"]) <= 7
    assert "NeoSuperpower workflow plugin" in manifest["description"]
    assert "NeoSuperpower workflows" in manifest["interface"]["shortDescription"]
    assert "Official NeoSuperpower workflow layer" in manifest["interface"]["longDescription"]
    default_prompt = "\n".join(manifest["interface"]["defaultPrompt"])
    assert "interpret the post-push atomic graph update result" in default_prompt
    assert "after push" not in default_prompt.lower()
    assert "refresh and verify the branch graph after push" not in default_prompt

    marketplace = _read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    entry = entries["neodev-rd-knowledge"]
    assert entry["source"] == {"source": "local", "path": "./plugins/neodev-rd-knowledge"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}


def test_official_plugin_workflows_cover_main_paths_and_use_cli_only():
    workflows = _read_json(PLUGIN_ROOT / "workflows" / "core-workflows.json")
    assert "local neodev CLI" in workflows["contract"]
    workflow_text = json.dumps(workflows, ensure_ascii=False)
    assert "refresh the branch graph after push" not in workflow_text
    assert "After successful push" not in workflow_text

    required = {
        "session_version_check",
        "doc_change_to_implementation",
        "repository_auto_graph",
        "pre_push_verification",
        "project_refresh_graph",
    }
    assert required.issubset(workflows["workflows"])

    all_commands = []
    for workflow in workflows["workflows"].values():
        assert workflow["goal"]
        assert workflow["steps"]
        for step in workflow["steps"]:
            assert step["type"] in {
                "browser",
                "cli",
                "diagnostic",
                "manual",
                "script",
                "skill",
                "user-confirmation",
                "workflow",
            }
        commands = [step["command"] for step in workflow["steps"] if step["type"] == "cli"]
        all_commands.extend(commands)

    assert all_commands
    joined = "\n".join(all_commands)
    assert "neodev config show" in joined
    assert "neodev cli version-check" in joined
    for expected in [
        "doc binding list --product-code <product_code> --json",
        "doc binding create --product-code <product_code> --version-name <version_name> --project-name <project_name> --repo-path <docs_repo_path> --branch <branch> --json",
        "doc import --doc-binding-id <doc_binding_id> --json",
        "doc change register",
        "graph impact",
        "project create --name <project_name> --repo-url <repo_url>",
        "project init-status --project-name <project_name> --branch <branch>",
        "product version bind-branch --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch <branch>",
        "git verify-doc-change",
        "git dangerous-commit list",
        "git dangerous-commit resolve",
        "project refresh-graph --project-name <project_name> --branch <branch>",
    ]:
        assert expected in joined
    assert "project refresh-commit-graph" not in joined
    assert "graph semantic-search" not in joined
    assert "product version analyze" not in joined
    assert "product version analyze-status" not in joined
    assert "product version watch-status" not in joined

    forbidden = re.compile(r"\b(psql|psycopg2|neo4j|cypher|insert\s+into|update\s+\w+\s+set)\b", re.I)
    assert not forbidden.search(joined)


def test_official_plugin_hooks_check_remote_cli_environment():
    hooks = _read_json(PLUGIN_ROOT / "hooks" / "hooks.json")
    hook_commands = []
    for phase in hooks["hooks"].values():
        for entry in phase:
            hook_commands.extend(hook["command"] for hook in entry["hooks"])

    joined = "\n".join(hook_commands)
    assert "session_start_hint.py" in joined
    assert "check_neodev_environment.py" in joined
    assert "ensure_git_guard.py" not in joined
    assert "git_guard_commit_msg.py" not in joined
    assert "git_guard_pre_push.py" not in joined
    assert "post_push_graph_update.py" in joined
    assert "echo \"After push" not in joined
    assert "neodev project refresh-commit-graph" not in joined
    assert "python neodev.py" not in joined


def test_official_skill_is_bundled_and_points_to_the_shared_workflow_contract():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert skill.startswith("---\n")
    assert "name: neodev-rd-knowledge" in skill
    assert "description: Use the local NeoDev CLI client against the configured remote NeoDev service" in skill
    assert "workflows/core-workflows.json" in skill
    assert "cli version-check" in skill
    assert "neodev config set-server" in skill
    assert "install-neodev-client.cmd" in skill
    assert "doc binding create" in skill
    assert "--project-name <project_name>" in skill
    assert "doc binding list --product-code <product_code> --json" in skill
    assert "doc import --doc-binding-id <doc_binding_id> --json" in skill
    assert "Use `--force` only when intentionally rebuilding existing chunks/embeddings" in skill
    assert "DocChange IDs are 40-character Git commit hashes" in skill
    assert "project create --name <project_name> --repo-url <repo_url>" in skill
    assert "product version analyze" not in skill
    assert "git verify-doc-change" not in skill
    assert "project refresh-graph" in skill
    assert "post_push_graph_update.py --json" in skill
    assert "git post-push-graph-update" in skill
    assert "server-side atomic" in skill
    assert "interpret_post_push_result" in skill
    assert "append_history+overwrite_latest" in skill
    assert "invalid_result" in skill
    assert "skill_hint mismatch" in skill
    assert "rollback_status=rolled_back" in skill
    assert "project refresh-commit-graph" not in skill
    assert "graph semantic-search" not in skill
    assert "PostgreSQL" in skill
    assert "Neo4j" in skill
    assert "## Session Checks" in skill
    assert "## Agent Post-Push Automation" in skill


def test_official_skill_prefers_primary_intent_commands():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "## Primary Intent Entries" in skill
    for expected in [
        "context: `neodev doctor`, `neodev context show`, `neodev setup repo`",
        "docs: `neodev docs sync`",
        "change: `neodev change start`, `neodev change impact`",
        "submit: `neodev git check`, `neodev status`",
    ]:
        assert expected in skill
    assert "Use atomic commands as advanced troubleshooting references" in skill


def test_official_plugin_guidance_does_not_suggest_manual_post_push_refresh():
    agent_guidance = (PLUGIN_ROOT / "agents" / "neodev-rd-knowledge.md").read_text(encoding="utf-8")
    cursor_rule = (PLUGIN_ROOT / "cursor" / "rules" / "neodev-git-docchange.mdc").read_text(encoding="utf-8")
    combined = "\n".join([agent_guidance, cursor_rule])

    assert "post-push atomic graph update" in combined
    assert "git post-push-graph-update" in combined
    assert "refresh the branch graph after push" not in combined
    assert "neodev project refresh-graph --project-id <project_id> --branch <branch> --json" not in combined


def test_official_plugin_commands_are_grouped_by_four_intents():
    command_root = PLUGIN_ROOT / "commands"
    command_files = {path.name for path in command_root.glob("*.md")}

    assert command_files == {
        "neodev-context.md",
        "neodev-docs.md",
        "neodev-change.md",
        "neodev-submit.md",
    }

    expected = {
        "neodev-context.md": ["neodev doctor", "neodev context show", "neodev setup repo"],
        "neodev-docs.md": ["neodev docs sync"],
        "neodev-change.md": ["neodev change start", "neodev change impact"],
        "neodev-submit.md": ["neodev git check", "neodev status"],
    }
    for filename, commands in expected.items():
        text = (command_root / filename).read_text(encoding="utf-8")
        assert "Primary intent entry" in text
        for command in commands:
            assert command in text
        assert "git post-push-graph-update" not in text
