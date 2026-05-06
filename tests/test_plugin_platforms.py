import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_rule_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.find("\n---", 4)
    assert end != -1
    return yaml.safe_load(text[4:end])


def test_codex_plugin_manifest_references_shared_hooks_and_scripts():
    manifest = _read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")

    neodev = manifest["neodev"]
    assert neodev["hooks"] == "./hooks/hooks.json"
    assert set(neodev["shared_scripts"]) == {
        "./validate_mvp_docs.py",
        "./validate_obsidian_docs.py",
        "./sync_obsidian_links.py",
        "./generate_mvp_doc.py",
        "./check_docchange_trailer.py",
        "./check_neodev_environment.py",
    }
    assert "Remote-service CLI" in neodev["contract"]
    assert "remote NeoDev service" in neodev["contract"]


def test_claude_plugin_contains_commands_agent_and_hook_schema():
    manifest = _read_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    assert manifest["name"] == "neodev-rd-knowledge"
    assert manifest["skills"] == "./skills/"
    assert manifest["commands"] == "./commands/"
    assert manifest["agents"] == "./agents/"
    assert manifest["hooks"] == "./hooks/hooks.json"

    for command_name in [
        "neodev-docchange",
        "neodev-doc-scan",
        "neodev-graph-impact",
        "neodev-project-refresh-graph",
    ]:
        command = (PLUGIN_ROOT / "commands" / f"{command_name}.md").read_text(
            encoding="utf-8"
        )
        assert "neodev" in command
        assert "--json" in command
        assert "remote NeoDev service" in command or "远程 NeoDev 服务" in command

    agent = (PLUGIN_ROOT / "agents" / "neodev-rd-knowledge.md").read_text(
        encoding="utf-8"
    )
    assert "local `neodev` CLI client" in agent
    assert "centralized remote NeoDev service" in agent
    assert "PostgreSQL" in agent
    assert "Neo4j" in agent

    hooks = _read_json(PLUGIN_ROOT / "hooks" / "hooks.json")
    assert set(hooks["hooks"]) == {"PostToolUse", "PreToolUse"}
    all_commands = "\n".join(
        hook["command"]
        for entries in hooks["hooks"].values()
        for entry in entries
        for hook in entry["hooks"]
    )
    assert "validate_mvp_docs.py" in all_commands
    assert "check_docchange_trailer.py" in all_commands
    assert "project refresh-graph" in all_commands
    assert "project refresh-commit-graph" not in all_commands
    assert "neodev doc import" in all_commands


def test_cursor_rules_exist_at_project_root_and_plugin_distribution_copy():
    expected = {
        "neodev-rd-knowledge.mdc": {"alwaysApply": True, "globs": "**/*"},
        "neodev-mvp-docs.mdc": {
            "alwaysApply": False,
            "globs": "**/*.md",
        },
        "neodev-git-docchange.mdc": {"alwaysApply": False, "globs": "**/*"},
    }

    for name, front_matter in expected.items():
        root_rule = ROOT / ".cursor" / "rules" / name
        plugin_rule = PLUGIN_ROOT / "cursor" / "rules" / name
        assert root_rule.exists()
        assert plugin_rule.exists()
        assert root_rule.read_text(encoding="utf-8") == plugin_rule.read_text(
            encoding="utf-8"
        )

        parsed = _read_rule_front_matter(root_rule)
        assert parsed["description"]
        assert parsed["globs"] == front_matter["globs"]
        assert parsed["alwaysApply"] is front_matter["alwaysApply"]
