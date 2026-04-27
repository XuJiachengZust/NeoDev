import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "neodev-rd-knowledge"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_official_plugin_manifest_and_marketplace_are_registered():
    manifest = _read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")

    assert manifest["name"] == "neodev-rd-knowledge"
    assert manifest["version"] == "0.1.0"
    assert manifest["skills"] == "./skills/"
    assert "neodev" in manifest["keywords"]
    assert manifest["interface"]["displayName"] == "NeoDev RD Knowledge"
    assert manifest["interface"]["capabilities"] == ["Workflow", "CLI orchestration"]
    assert len(manifest["interface"]["defaultPrompt"]) <= 3

    marketplace = _read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    entry = entries["neodev-rd-knowledge"]
    assert entry["source"] == {"source": "local", "path": "./plugins/neodev-rd-knowledge"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "Developer Tools"


def test_official_plugin_workflows_cover_main_paths_and_use_cli_only():
    workflows = _read_json(PLUGIN_ROOT / "workflows" / "core-workflows.json")

    required = {
        "session_version_check",
        "doc_change_to_implementation",
        "branch_analysis",
        "pre_push_verification",
        "post_push_refresh",
    }
    assert required.issubset(workflows["workflows"])

    all_commands = []
    for workflow in workflows["workflows"].values():
        commands = [step["command"] for step in workflow["steps"] if step["type"] == "cli"]
        assert commands[0].startswith("python neodev.py cli version-check")
        all_commands.extend(commands)

    joined = "\n".join(all_commands)
    for expected in [
        "doc change register",
        "graph impact",
        "product version analyze",
        "product version analyze-status",
        "git verify-doc-change",
        "git dangerous-commit list",
        "git dangerous-commit resolve",
        "git post-push-refresh",
    ]:
        assert expected in joined

    forbidden = re.compile(r"\b(psql|psycopg2|neo4j|cypher|insert\s+into|update\s+\w+\s+set)\b", re.I)
    assert not forbidden.search(joined)


def test_official_skill_is_bundled_and_points_to_the_shared_workflow_contract():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert skill.startswith("---\n")
    assert "name: neodev-rd-knowledge" in skill
    assert "description:" in skill
    assert "workflows/core-workflows.json" in skill
    assert "cli version-check" in skill
    assert "git verify-doc-change" in skill
    assert "git post-push-refresh" in skill
    assert "不要直接写 PostgreSQL" in skill
    assert "不要直接写 Neo4j" in skill
