"""Unit tests for layered parallel AI analysis runner."""


def test_run_ai_analysis_layered_order_and_index_once(monkeypatch):
    from service.services import ai_analysis_runner as runner

    sequence: list[tuple[str, str]] = []
    ensured_dims: list[int] = []

    nodes = [
        {
            "id": "L",
            "label": "Function",
            "name": "leaf",
            "description": "",
            "child_count": 0,
            "sourceCode": "function leaf() end",
        },
        {"id": "M", "label": "Class", "name": "mid", "description": "", "child_count": 1, "sourceCode": None},
        {"id": "R", "label": "Project", "name": "root", "description": "", "child_count": 1, "sourceCode": None},
    ]
    edges = [("M", "L"), ("R", "M")]

    monkeypatch.setattr(runner, "get_llm_config", lambda: {"api_key": "k", "model_embedding": "embed-x"})
    monkeypatch.setattr(runner, "_load_nodes", lambda *_args, **_kwargs: nodes)
    monkeypatch.setattr(runner, "_load_contains_edges", lambda *_args, **_kwargs: edges)
    monkeypatch.setattr(runner, "_max_workers", lambda: 2)
    monkeypatch.setattr(runner, "_progress_interval", lambda: 1)
    monkeypatch.setattr(runner, "_sample_size", lambda: 3)
    monkeypatch.setattr(
        runner,
        "_ensure_vector_indexes",
        lambda *args, **kwargs: ensured_dims.append(kwargs["dimensions"]),
    )

    def _leaf(**kwargs):
        node = kwargs["node"]
        sequence.append(("leaf", node["id"]))
        return {
            "status": "saved",
            "node_id": node["id"],
            "label": node["label"],
            "name": node["name"],
            "worker": "w",
            "embedding_dim": 3,
            "duration_ms": 10,
        }

    def _container(**kwargs):
        node = kwargs["node"]
        sequence.append(("container", node["id"]))
        return {
            "status": "saved",
            "node_id": node["id"],
            "label": node["label"],
            "name": node["name"],
            "worker": "w",
            "embedding_dim": 3,
            "duration_ms": 12,
        }

    monkeypatch.setattr(runner, "_process_leaf_node", _leaf)
    monkeypatch.setattr(runner, "_process_container_node", _container)

    process_logs: list[dict] = []
    stats = runner.run_ai_analysis(
        neo4j_driver=object(),
        project_id=1,
        branch="main",
        force=True,
        process_logs=process_logs,
        database=None,
    )

    assert sequence == [("leaf", "L"), ("container", "M"), ("container", "R")]
    assert stats["saved"] == 3
    assert stats["embedded"] == 3
    assert stats["failed"] == 0
    assert ensured_dims == [3]
    stages = [item.get("stage") for item in process_logs]
    assert "LEAF_PARALLEL" in stages
    assert "CONTAINER_LEVEL_1" in stages
    assert "CONTAINER_LEVEL_2" in stages
    assert "FINISH" in stages


def test_run_ai_analysis_failure_isolated(monkeypatch):
    from service.services import ai_analysis_runner as runner

    nodes = [
        {"id": "A", "label": "Function", "name": "a", "description": "", "child_count": 0, "sourceCode": "code A"},
        {"id": "B", "label": "Function", "name": "b", "description": "", "child_count": 0, "sourceCode": "code B"},
    ]

    monkeypatch.setattr(runner, "get_llm_config", lambda: {"api_key": "k", "model_embedding": "embed-x"})
    monkeypatch.setattr(runner, "_load_nodes", lambda *_args, **_kwargs: nodes)
    monkeypatch.setattr(runner, "_load_contains_edges", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runner, "_max_workers", lambda: 2)
    monkeypatch.setattr(runner, "_progress_interval", lambda: 1)
    monkeypatch.setattr(runner, "_sample_size", lambda: 3)
    monkeypatch.setattr(runner, "_ensure_vector_indexes", lambda *args, **kwargs: None)

    def _leaf(**kwargs):
        node = kwargs["node"]
        if node["id"] == "A":
            return {
                "status": "failed",
                "step": "desc",
                "node_id": "A",
                "label": "Function",
                "name": "a",
                "worker": "w1",
                "error_type": "RuntimeError",
                "error_message": "bad llm",
                "duration_ms": 3,
            }
        return {
            "status": "saved",
            "node_id": "B",
            "label": "Function",
            "name": "b",
            "worker": "w2",
            "embedding_dim": 3,
            "duration_ms": 5,
        }

    monkeypatch.setattr(runner, "_process_leaf_node", _leaf)
    monkeypatch.setattr(runner, "_process_container_node", lambda **kwargs: kwargs)

    logs: list[dict] = []
    stats = runner.run_ai_analysis(
        neo4j_driver=object(),
        project_id=1,
        branch="main",
        force=True,
        process_logs=logs,
        database=None,
    )

    assert stats["saved"] == 1
    assert stats["embedded"] == 1
    assert stats["failed"] == 1
    assert stats["failed_desc"] == 1
    assert len(stats["failures"]) == 1
    assert stats["failures"][0]["node_id"] == "A"
    assert any(item.get("message") == "节点处理失败" for item in logs)
