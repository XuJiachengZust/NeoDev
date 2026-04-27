import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_ROOT = ROOT / "examples" / "neodev-rd-knowledge"


def test_minimal_e2e_example_contains_reproducible_product_doc_and_project_scope():
    manifest = json.loads((EXAMPLE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["product"]["code"] == "NEODEV-DEMO"
    assert manifest["product"]["version"] == "V1.0"
    assert manifest["doc_repository"]["path"] == "doc-repo"
    assert set(manifest["doc_repository"]["required_directories"]) == {
        "prd",
        "prototype",
        "tech-design",
    }
    assert len(manifest["project_branches"]) == 2
    assert {item["branch"] for item in manifest["project_branches"]} == {
        "main",
        "feature/docchange-demo",
    }

    assert (EXAMPLE_ROOT / "doc-repo" / "prd" / "NEODEV-DEMO-V1.md").exists()
    assert (EXAMPLE_ROOT / "doc-repo" / "prototype" / ".gitkeep").exists()
    assert (EXAMPLE_ROOT / "doc-repo" / "tech-design" / "NEODEV-DEMO-TECH.md").exists()
    assert (EXAMPLE_ROOT / "project-repo" / "src" / "demo_service.py").exists()

    for path in [
        EXAMPLE_ROOT / "doc-repo" / "prd" / "NEODEV-DEMO-V1.md",
        EXAMPLE_ROOT / "doc-repo" / "tech-design" / "NEODEV-DEMO-TECH.md",
    ]:
        text = path.read_text(encoding="utf-8")
        end = text.find("\n---", 4)
        front_matter = yaml.safe_load(text[4:end])
        assert front_matter["product_key"] == "NEODEV-DEMO"
        assert front_matter["status"] in {"draft", "active", "deprecated"}
        assert isinstance(front_matter["relations"]["target"], list)


def test_minimal_e2e_demo_steps_use_plugin_skill_and_cli_chain():
    manifest = json.loads((EXAMPLE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    commands = [step["command"] for step in manifest["demo_steps"] if step["type"] == "cli"]

    assert manifest["plugin"] == "neodev-rd-knowledge"
    assert manifest["skill"] == "neodev-rd-knowledge"
    assert commands[0] == "neodev config show"
    assert commands[1].startswith("neodev cli version-check")

    joined = "\n".join(commands)
    for expected in [
        "product create",
        "product version create",
        "product version bind-branch",
        "doc scan",
        "doc change register",
        "graph impact",
        "git verify-doc-change",
        "git post-push-refresh",
    ]:
        assert expected in joined

    guide = (EXAMPLE_ROOT / "README.md").read_text(encoding="utf-8")
    assert "plugins/neodev-rd-knowledge/workflows/core-workflows.json" in guide
    assert "neodev config set-server <remote-url>" in guide
    assert "不要直接写 PostgreSQL" in guide
    assert "不要直接写 Neo4j" in guide
