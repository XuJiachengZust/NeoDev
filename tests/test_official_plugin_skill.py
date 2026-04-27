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
    assert manifest["version"] == "0.1.0"
    assert manifest["skills"] == "./skills/"
    assert "neodev" in manifest["keywords"]
    assert manifest["interface"]["displayName"] == "NeoDev 研发知识插件"
    assert manifest["interface"]["capabilities"] == ["工作流编排", "CLI 调用引导"]
    assert len(manifest["interface"]["defaultPrompt"]) <= 3
    assert _contains_cjk(manifest["description"])
    assert _contains_cjk(manifest["interface"]["shortDescription"])
    assert _contains_cjk(manifest["interface"]["longDescription"])
    assert all(_contains_cjk(prompt) for prompt in manifest["interface"]["defaultPrompt"])

    marketplace = _read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert marketplace["interface"]["displayName"] == "NeoDev 本地插件市场"
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    entry = entries["neodev-rd-knowledge"]
    assert entry["source"] == {"source": "local", "path": "./plugins/neodev-rd-knowledge"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "开发者工具"


def test_official_plugin_workflows_cover_main_paths_and_use_cli_only():
    workflows = _read_json(PLUGIN_ROOT / "workflows" / "core-workflows.json")
    assert _contains_cjk(workflows["contract"])

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
        assert _contains_cjk(workflow["goal"])
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
    assert "description: 用于 NeoDev 研发知识工作流" in skill
    assert "workflows/core-workflows.json" in skill
    assert "cli version-check" in skill
    assert "git verify-doc-change" in skill
    assert "git post-push-refresh" in skill
    assert "不要直接写 PostgreSQL" in skill
    assert "不要直接写 Neo4j" in skill
    assert "## 必守边界" in skill
    assert "## 主流程" in skill
    for old_text in [
        "Use this skill",
        "Required Boundary",
        "Workflow Source",
        "Main Flows",
        "Result Interpretation",
    ]:
        assert old_text not in skill
