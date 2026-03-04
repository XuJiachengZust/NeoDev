"""Configuration from dict, env, or config file. No hardcoded paths."""

import json
import os
from pathlib import Path
from typing import Any

# Env keys (optional override)
ENV_NEO4J_URI = "NEO4J_URI"
ENV_NEO4J_USER = "NEO4J_USER"
ENV_NEO4J_PASSWORD = "NEO4J_PASSWORD"
ENV_REPO_PATH = "REPO_PATH"  # Legacy: pipeline no longer reads repo from config; for backward compat only


def load_config(source: dict | str | Path | None = None) -> dict[str, Any]:
    """
    Load config from dict, file path, or env. Config only holds repo-unrelated options
    (e.g. neo4j_uri, neo4j_user, neo4j_password, neo4j_database). Repo path, repo URL,
    clone dir, and branches are passed via method parameters, not via config.
    - dict: use as base, then override with env
    - str/Path: path to JSON file (neo4j_* keys only), then override with env
    - None: only env vars
    """
    config: dict[str, Any] = {}
    if isinstance(source, dict):
        config = dict(source)
    elif source is not None:
        path = Path(source)
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
    if os.environ.get(ENV_NEO4J_URI):
        config["neo4j_uri"] = os.environ[ENV_NEO4J_URI]
    if os.environ.get(ENV_NEO4J_USER):
        config["neo4j_user"] = os.environ[ENV_NEO4J_USER]
    if os.environ.get(ENV_NEO4J_PASSWORD):
        config["neo4j_password"] = os.environ[ENV_NEO4J_PASSWORD]
    if os.environ.get(ENV_REPO_PATH):
        config["repo_path"] = os.environ[ENV_REPO_PATH]
    return config
