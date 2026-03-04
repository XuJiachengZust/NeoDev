"""Contract tests: config must not contain repo_path, repo_url, or branches."""

import json
from pathlib import Path

import pytest


# Path to config.example.json relative to repo root (project root)
CONFIG_EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "src" / "config.example.json"

REPO_KEYS_FORBIDDEN = ("repo_path", "repo_url", "branches")


def test_config_example_does_not_contain_repo_or_branches():
    """config.example.json must not contain repo_path, repo_url, or branches."""
    assert CONFIG_EXAMPLE_PATH.is_file(), f"Expected {CONFIG_EXAMPLE_PATH} to exist"
    with open(CONFIG_EXAMPLE_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    for key in REPO_KEYS_FORBIDDEN:
        assert key not in config, f"config.example.json must not contain '{key}' (repo/branches come from method params)"


def test_load_config_accepts_neo4j_only_dict():
    """load_config from dict with only neo4j_* keys should not require repo keys."""
    from gitnexus_parser.config import load_config

    cfg = load_config({
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "secret",
    })
    assert "neo4j_uri" in cfg
    assert "neo4j_user" in cfg
    assert "neo4j_password" in cfg
