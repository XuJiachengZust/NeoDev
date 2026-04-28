"""Neo4j configuration loading shared by graph query services."""


def load_neo4j_config(project: dict) -> tuple[dict | None, str | None]:
    import os
    from pathlib import Path

    config = {}
    try:
        from gitnexus_parser import load_config

        config = load_config()
        if not config.get("neo4j_uri"):
            src_dir = Path(__file__).resolve().parent.parent.parent
            for path in [src_dir / "config.json", src_dir / "config.example.json"]:
                if path.is_file():
                    try:
                        config = load_config(path)
                        if config.get("neo4j_uri"):
                            break
                    except Exception:
                        pass
    except Exception:
        pass
    if not config.get("neo4j_uri"):
        return None, None
    db = (project.get("neo4j_database") or "").strip() or config.get("neo4j_database")
    return config, (db if db else None)
