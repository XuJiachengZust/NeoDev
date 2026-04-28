import hashlib
import shutil
import uuid
from pathlib import Path

from gitnexus_parser.graph import generate_id


def _local_tmp_dir(name: str) -> Path:
    root = Path(__file__).resolve().parent.parent / ".test-tmp" / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_create_snapshot_from_repo_records_supported_file_entries(monkeypatch):
    from service.services import branch_snapshot_service

    tmp_path = _local_tmp_dir(f"branch-snapshot-{uuid.uuid4().hex[:8]}")
    source = tmp_path / "src" / "app.py"
    try:
        source.parent.mkdir()
        source.write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# ignored\n", encoding="utf-8")

        calls = {}

        monkeypatch.setattr(
            branch_snapshot_service.snapshot_repo,
            "get_current_snapshot",
            lambda conn, project_id, branch: {"id": 7},
        )

        def fake_create_snapshot(conn, **kwargs):
            calls["snapshot"] = kwargs
            return {"id": 42, **kwargs}

        def fake_replace_entries(conn, snapshot_id, entries):
            calls["entries"] = {"snapshot_id": snapshot_id, "entries": entries}
            return len(entries)

        monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "create_snapshot", fake_create_snapshot)
        monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "replace_entries", fake_replace_entries)

        snapshot = branch_snapshot_service.create_snapshot_from_repo(
            object(),
            repo_path=str(tmp_path),
            project_id=3,
            branch="main",
            head_commit="a" * 40,
            last_parsed_commit="a" * 40,
            created_from_action="incremental",
        )

        assert snapshot["id"] == 42
        assert calls["snapshot"]["repo_id"] == 3
        assert calls["snapshot"]["branch"] == "main"
        assert calls["snapshot"]["base_snapshot_id"] == 7
        assert calls["snapshot"]["created_from_action"] == "incremental"

        entries = calls["entries"]["entries"]
        file_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        assert calls["entries"]["snapshot_id"] == 42
        assert entries == [
            {
                "project_id": 3,
                "repo_id": 3,
                "file_path": "src/app.py",
                "file_node_id": generate_id("File", f"repo:3:file:src/app.py:hash:{file_hash}"),
                "file_content_hash": file_hash,
                "visible": True,
            }
        ]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_clone_snapshot_copies_entries_with_copy_data_action(monkeypatch):
    from service.services import branch_snapshot_service

    calls = {}

    def fake_create_snapshot(conn, **kwargs):
        calls["snapshot"] = kwargs
        return {"id": 88, **kwargs}

    def fake_copy_entries(conn, source_snapshot_id, target_snapshot_id, *, project_id, repo_id):
        calls["copy"] = {
            "source_snapshot_id": source_snapshot_id,
            "target_snapshot_id": target_snapshot_id,
            "project_id": project_id,
            "repo_id": repo_id,
        }
        return 2

    monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "create_snapshot", fake_create_snapshot)
    monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "copy_entries", fake_copy_entries)

    snapshot = branch_snapshot_service.clone_snapshot(
        object(),
        source_snapshot_id=55,
        project_id=9,
        branch="release",
        head_commit="b" * 40,
        last_parsed_commit="b" * 40,
    )

    assert snapshot["id"] == 88
    assert snapshot["created_from_action"] == "copy_data"
    assert snapshot["base_snapshot_id"] == 55
    assert snapshot["entry_count"] == 2
    assert calls["copy"] == {
        "source_snapshot_id": 55,
        "target_snapshot_id": 88,
        "project_id": 9,
        "repo_id": 9,
    }


def test_commit_incremental_snapshot_uses_current_snapshot_as_base(monkeypatch):
    from service.services import branch_snapshot_service

    tmp_path = _local_tmp_dir(f"branch-snapshot-commit-{uuid.uuid4().hex[:8]}")
    try:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        calls = {}

        monkeypatch.setattr(
            branch_snapshot_service.snapshot_repo,
            "get_current_snapshot",
            lambda conn, project_id, branch: {"id": 123},
        )

        def fake_create_snapshot(conn, **kwargs):
            calls["snapshot"] = kwargs
            return {"id": 456, **kwargs}

        monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "create_snapshot", fake_create_snapshot)
        monkeypatch.setattr(
            branch_snapshot_service.snapshot_repo,
            "replace_entries",
            lambda conn, snapshot_id, entries: len(entries),
        )

        snapshot = branch_snapshot_service.create_snapshot_from_repo(
            object(),
            repo_path=str(tmp_path),
            project_id=3,
            branch="main",
            head_commit="b" * 40,
            last_parsed_commit="b" * 40,
            created_from_action="commit_incremental",
        )

        assert snapshot["id"] == 456
        assert calls["snapshot"]["base_snapshot_id"] == 123
        assert calls["snapshot"]["created_from_action"] == "commit_incremental"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
