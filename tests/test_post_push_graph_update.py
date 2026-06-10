import json
import os
import shutil
import subprocess
import sys
import uuid
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"
POST_PUSH = PLUGIN_ROOT / "post_push_graph_update.py"
HOOKS = PLUGIN_ROOT / "hooks" / "hooks.json"


def _tmp_repo(name: str) -> Path:
    root = ROOT / ".test-tmp" / f"{name}-{uuid.uuid4().hex[:8]}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "NeoDev Tests"], cwd=root, check=True)
    return root


def _commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True, text=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def _empty_commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "commit", "--allow-empty", "-m", message], cwd=repo, check=True, capture_output=True, text=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def _write_project_config(repo: Path, **values) -> None:
    config = repo / ".neodev" / "project.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps(values), encoding="utf-8")


def _write_stub(
    repo: Path,
    *,
    fail_atomic: bool = False,
    refresh_head: bool | str = True,
    rollback_status: str = "rolled_back",
    remote_project_name: str | None = None,
) -> tuple[Path, Path]:
    calls = repo / "neodev_calls.jsonl"
    stub = repo / "neodev_stub.py"
    stub.write_text(
        "import json, pathlib, subprocess, sys\n"
        f"calls = pathlib.Path({str(calls)!r})\n"
        "args = sys.argv[1:]\n"
        "with calls.open('a', encoding='utf-8') as fh:\n"
        "    fh.write(json.dumps(args) + '\\n')\n"
        "command = ' '.join(args[:2])\n"
        "if args[:2] == ['git', 'post-push-graph-update']:\n"
        f"    fail = {str(fail_atomic)}\n"
        "    request = json.loads(pathlib.Path(args[args.index('--payload-file') + 1]).read_text(encoding='utf-8'))\n"
        "    if fail:\n"
        f"        print(json.dumps({{'ok': False, 'command': 'git post-push-graph-update', 'data': None, 'errors': [{{'category': 'internal_error', 'message': 'atomic update failed', 'details': {{'rollback_status': {rollback_status!r}, 'operation_id': 'op-1'}}}}]}}))\n"
        "        raise SystemExit(10)\n"
        "    commit_results = request.get('commit_results') or []\n"
        "    doc_commits = [item for item in commit_results if item.get('scope') == 'document' and item.get('documents')]\n"
        "    code_commits = [item for item in commit_results if item.get('scope') == 'code']\n"
        "    documents = [{'id': 21 + index, 'relative_path': item['documents'][0]} for index, item in enumerate(doc_commits)]\n"
        "    doc_import_results = []\n"
        "    if doc_commits:\n"
        "        doc_import_results.append({'doc_binding_id': request.get('project', {}).get('doc_binding_id'), 'imported_count': len(documents), 'documents': documents})\n"
        "    doc_register = [{'status': 'registered', 'commit_sha': item['commit_sha'], 'relative_path': item['documents'][0], 'doc_change_id': item['commit_sha']} for item in doc_commits]\n"
        "    links = [{'status': 'verified', 'commit_sha': item['commit_sha'], 'doc_change_id': item.get('doc_change_id'), 'code_change_link': {'commit_sha': item['commit_sha']}} for item in code_commits]\n"
        f"    remote_project_name = {remote_project_name!r}\n"
        "    data = {'status': 'completed', 'operation_id': 'op-1', 'atomic': True, 'project': {'project_id': request.get('project', {}).get('project_id') or 13, 'project_name': remote_project_name or request.get('project', {}).get('project_name'), 'branch': request.get('branch')}, 'doc_import_results': doc_import_results, 'docchange_register_results': doc_register, 'docchange_link_results': links, 'graph_refresh_result': {'status': 'completed', 'graph_id': 'graph-1', 'node_count': 3, 'edge_count': 2}, 'rollback_status': 'not_needed'}\n"
        f"    include_head = {refresh_head!r}\n"
        "    if include_head == 'git':\n"
        "        data['graph_refresh_result']['head_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()\n"
        "    elif include_head:\n"
        "        data['graph_refresh_result']['head_commit'] = 'h' * 40\n"
        "    print(json.dumps({'ok': True, 'command': 'git post-push-graph-update', 'data': data, 'errors': []}))\n"
        "else:\n"
        "    print(json.dumps({'ok': False, 'command': command, 'data': None, 'errors': [{'category': 'invalid_argument', 'message': 'unexpected command', 'details': {'args': args}}]}))\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    return stub, calls


def _run_post_push(repo: Path, stub: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(POST_PUSH), "--repo-root", str(repo), "--json"],
        cwd=repo,
        env={**os.environ, "NEODEV_CLI": f"{sys.executable} {stub}"},
        text=True,
        capture_output=True,
        check=False,
    )


def _payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)


def _load_post_push_module():
    if str(PLUGIN_ROOT) not in sys.path:
        sys.path.insert(0, str(PLUGIN_ROOT))
    spec = importlib.util.spec_from_file_location(f"post_push_graph_update_{uuid.uuid4().hex}", POST_PUSH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _calls(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _atomic_request(calls: list[list[str]]) -> dict:
    assert len(calls) == 1
    call = calls[0]
    assert call[:2] == ["git", "post-push-graph-update"]
    payload_file = Path(call[call.index("--payload-file") + 1])
    return json.loads(payload_file.read_text(encoding="utf-8"))


def test_post_push_hook_command_resolves_same_directory_imports():
    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))
    command = next(
        hook["command"]
        for entry in hooks["hooks"]["PostToolUse"]
        if entry["matcher"] == "Bash(git push *)"
        for hook in entry["hooks"]
    )
    cwd = ROOT / ".test-tmp" / f"post-push-hook-{uuid.uuid4().hex[:8]}"
    cwd.mkdir(parents=True)
    try:
        subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True, text=True)
        proc = subprocess.run(
            command,
            cwd=cwd,
            env={**os.environ, "NEODEV_RD_KNOWLEDGE_PLUGIN_ROOT": str(PLUGIN_ROOT)},
            text=True,
            capture_output=True,
            shell=True,
            check=False,
        )

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["hook_status"] == "not_ready"
        assert payload["errors"][0]["category"] == "not_ready"
        assert "ModuleNotFoundError" not in proc.stderr
    finally:
        shutil.rmtree(cwd, ignore_errors=True)


def test_post_push_code_commit_calls_atomic_cli_once_and_maps_results():
    repo = _tmp_repo("post-push-code")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        commit_sha = _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 0, proc.stderr
        assert payload["hook_status"] == "success"
        assert payload["classification_summary"]["code"] == 1
        assert payload["docchange_link_results"][0]["commit_sha"] == commit_sha
        assert payload["graph_refresh_result"]["status"] == "completed"
        assert payload["run_record"]["persistence_mode"] == "append_history+overwrite_latest"
        assert payload["skill_hint"] == {
            "skill": "neodev-rd-knowledge",
            "action": "interpret_post_push_result",
        }
        assert (repo / ".neodev" / "post_push_graph_update" / "history.jsonl").exists()
        assert (repo / ".neodev" / "post_push_graph_update" / "latest.json").exists()
        called = _calls(calls)
        request = _atomic_request(called)
        assert request["commit_range"] == [commit_sha]
        assert request["commit_results"][0]["doc_change_id"] == "a" * 40
        assert request["commit_results"][0]["commit_sha"] == commit_sha
        assert request["commit_results"][0]["route"] == "atomic_post_push_update"
        assert all(call[:2] != ["git", "verify-doc-change"] for call in called)
        assert all(call[:2] != ["project", "refresh-graph"] for call in called)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_rejects_refresh_result_without_head_commit():
    repo = _tmp_repo("post-push-head-fallback")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, calls = _write_stub(repo, refresh_head=False)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["hook_status"] == "failed"
        assert payload["rollback_status"] == "rollback_failed"
        assert payload["errors"][0]["category"] == "invalid_result"
        request = _atomic_request(_calls(calls))
        assert request["commit_results"][0]["scope"] == "code"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_initial_run_uses_upstream_reflog_for_multiple_pushed_commits():
    root = ROOT / ".test-tmp" / f"post-push-multi-{uuid.uuid4().hex[:8]}"
    remote = root / "remote.git"
    repo = root / "repo"
    try:
        root.mkdir(parents=True)
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "clone", str(remote), str(repo)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "NeoDev Tests"], cwd=repo, check=True)
        _write_project_config(repo, project_id=13)
        (repo / "init.py").write_text("print('init')\n", encoding="utf-8")
        _commit(repo, "feat: init\n\nDocChange-ID: " + "a" * 40)
        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=repo, check=True, capture_output=True, text=True)
        (repo / "one.py").write_text("print('one')\n", encoding="utf-8")
        first = _commit(repo, "feat: one\n\nDocChange-ID: " + "b" * 40)
        (repo / "two.py").write_text("print('two')\n", encoding="utf-8")
        second = _commit(repo, "feat: two\n\nDocChange-ID: " + "c" * 40)
        subprocess.run(["git", "push"], cwd=repo, check=True, capture_output=True, text=True)
        stub, calls = _write_stub(repo, refresh_head="git")

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 0, proc.stderr
        assert payload["commit_range"] == [first, second]
        assert [item["commit_sha"] for item in payload["docchange_link_results"]] == [first, second]
        request = _atomic_request(_calls(calls))
        assert request["commit_range"] == [first, second]
        assert [item["commit_sha"] for item in request["commit_results"]] == [first, second]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_post_push_document_commit_calls_atomic_cli_once_and_maps_doc_results():
    repo = _tmp_repo("post-push-doc")
    try:
        _write_project_config(repo, project_id=13, doc_binding_id=7)
        doc = repo / "docs" / "requirements" / "example.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Example\n", encoding="utf-8")
        commit_sha = _commit(repo, "docs: update requirement")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 0, proc.stderr
        assert payload["hook_status"] == "success"
        assert payload["classification_summary"]["document"] == 1
        assert payload["doc_import_results"][0]["doc_binding_id"] == 7
        assert payload["docchange_register_results"][0]["doc_change_id"] == commit_sha
        called = _calls(calls)
        request = _atomic_request(called)
        assert request["project"]["doc_binding_id"] == 7
        assert request["commit_results"][0]["documents"] == ["docs/requirements/example.md"]
        assert all(call[:2] != ["doc", "import"] for call in called)
        assert all(call[:3] != ["doc", "change", "register"] for call in called)
        assert all(call[:2] != ["project", "refresh-graph"] for call in called)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_code_commit_without_docchange_trailer_fails_before_remote_cli_writes():
    repo = _tmp_repo("post-push-code-no-docchange")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        _commit(repo, "feat: implement")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["hook_status"] == "failed"
        assert payload["rollback_status"] == "not_needed"
        assert payload["classification_summary"]["code"] == 1
        assert payload["errors"][0]["category"] == "invalid_argument"
        assert _calls(calls) == []
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_mixed_commit_fails_before_remote_cli_writes():
    repo = _tmp_repo("post-push-mixed")
    try:
        _write_project_config(repo, project_id=13, doc_binding_id=7)
        (repo / "app.py").write_text("print('mixed')\n", encoding="utf-8")
        doc = repo / "docs" / "requirements" / "example.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Example\n", encoding="utf-8")
        _commit(repo, f"feat: mixed\n\nDocChange-ID: {'a' * 40}")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["hook_status"] == "failed"
        assert payload["classification_summary"]["mixed"] == 1
        assert payload["rollback_status"] == "not_needed"
        assert payload["errors"][0]["category"] == "invalid_scope"
        assert _calls(calls) == []
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_rejects_multi_document_commit_before_remote_cli_writes():
    repo = _tmp_repo("post-push-multi-doc")
    try:
        _write_project_config(repo, project_id=13, doc_binding_id=7)
        first = repo / "docs" / "requirements" / "first.md"
        second = repo / "docs" / "requirements" / "second.md"
        first.parent.mkdir(parents=True)
        first.write_text("# First\n", encoding="utf-8")
        second.write_text("# Second\n", encoding="utf-8")
        _commit(repo, "docs: update two docs")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["hook_status"] == "failed"
        assert payload["errors"][0]["category"] == "invalid_scope"
        assert _calls(calls) == []
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_empty_commit_skips_without_refresh():
    repo = _tmp_repo("post-push-empty")
    try:
        _write_project_config(repo, project_id=13)
        _empty_commit(repo, "chore: empty")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 0, proc.stderr
        assert payload["hook_status"] == "skipped"
        assert payload["classification_summary"]["empty"] == 1
        assert _calls(calls) == []
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_latest_head_uses_project_business_key():
    repo = _tmp_repo("post-push-latest-key")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        commit_sha = _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        state = repo / ".neodev" / "post_push_graph_update"
        state.mkdir(parents=True)
        (state / "latest.json").write_text(
            json.dumps(
                {
                    "project:99:branch:master": {
                        "project": {"project_id": 99, "branch": "master"},
                        "graph_refresh_result": {"head_commit": commit_sha},
                    }
                }
            ),
            encoding="utf-8",
        )
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 0, proc.stderr
        assert payload["hook_status"] == "success"
        request = _atomic_request(_calls(calls))
        assert request["commit_range"] == [commit_sha]
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_resolves_project_id_for_code_commit_from_project_name():
    repo = _tmp_repo("post-push-project-name")
    try:
        _write_project_config(repo, project_name="NeoDev")
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, calls = _write_stub(repo)

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 0, proc.stderr
        assert payload["project"]["project_id"] == 13
        called = _calls(calls)
        request = _atomic_request(called)
        assert request["project"]["project_name"] == "NeoDev"
        assert request["project"]["project_id"] is None
        assert all(call[:2] != ["project", "show"] for call in called)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_parses_quoted_windows_neodev_cli(monkeypatch):
    module = _load_post_push_module()
    monkeypatch.setenv("NEODEV_CLI", '"C:\\Program Files\\NeoDev\\neodev.exe" --server http://example.invalid')

    cli = module._resolve_cli()

    assert cli[0] == "C:\\Program Files\\NeoDev\\neodev.exe"
    assert cli[1:] == ["--server", "http://example.invalid"]


def test_post_push_reports_server_atomic_failure_without_plugin_partial_write_assumption():
    repo = _tmp_repo("post-push-refresh-fails")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, calls = _write_stub(repo, fail_atomic=True, rollback_status="rolled_back")

        proc = _run_post_push(repo, stub)

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["hook_status"] == "failed"
        assert payload["rollback_status"] == "rolled_back"
        assert payload["errors"][0]["message"] == "atomic update failed"
        assert "rollback_summary" not in payload
        assert payload["run_record"]["latest_status"] == "failed"
        _atomic_request(_calls(calls))
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_reports_persistence_failure_as_structured_error(monkeypatch):
    repo = _tmp_repo("post-push-persist-fails")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, _ = _write_stub(repo, refresh_head="git")
        monkeypatch.setenv("NEODEV_CLI", f"{sys.executable} {stub}")
        module = _load_post_push_module()

        def fail_persist(repo_root, payload):
            raise OSError("disk full")

        monkeypatch.setattr(module, "_persist_run", fail_persist)

        payload = module.run_post_push(repo)

        assert payload["hook_status"] == "failed"
        assert payload["rollback_status"] == "rollback_failed"
        assert payload["errors"][-1]["category"] == "persistence_failed"
        assert payload["run_record"]["latest_status"] == "failed"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_skip_persists_single_history_line():
    repo = _tmp_repo("post-push-skip-once")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, _ = _write_stub(repo, refresh_head="git")
        first = _run_post_push(repo, stub)
        assert first.returncode == 0, first.stderr

        second = _run_post_push(repo, stub)

        payload = _payload(second)
        assert payload["hook_status"] == "skipped"
        history = repo / ".neodev" / "post_push_graph_update" / "history.jsonl"
        assert len(history.read_text(encoding="utf-8").splitlines()) == 2
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_post_push_repeated_skip_keeps_previous_success_head():
    repo = _tmp_repo("post-push-skip-repeat")
    try:
        _write_project_config(repo, project_id=13)
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        commit_sha = _commit(repo, f"feat: implement\n\nDocChange-ID: {'a' * 40}")
        stub, calls = _write_stub(repo, refresh_head="git", remote_project_name="remote-project-name")

        first = _run_post_push(repo, stub)
        second = _run_post_push(repo, stub)
        third = _run_post_push(repo, stub)

        assert first.returncode == 0, first.stderr
        assert second.returncode == 0, second.stderr
        payload = _payload(third)
        assert third.returncode == 0, third.stderr
        assert payload["hook_status"] == "skipped"
        assert payload["graph_refresh_result"]["head_commit"] == commit_sha
        assert len(_calls(calls)) == 1
    finally:
        shutil.rmtree(repo, ignore_errors=True)
