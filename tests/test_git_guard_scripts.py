import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"
ENSURE_GUARD = PLUGIN_ROOT / "ensure_git_guard.py"
COMMIT_GUARD = PLUGIN_ROOT / "git_guard_commit_msg.py"
PRE_PUSH_GUARD = PLUGIN_ROOT / "git_guard_pre_push.py"


def _hook_command(script_name: str) -> str:
    hooks = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    for entries in hooks["hooks"].values():
        for entry in entries:
            for hook in entry["hooks"]:
                command = hook["command"]
                if script_name in command:
                    return command
    raise AssertionError(f"hook command not found for {script_name}")


def _tmp_repo(name: str) -> Path:
    root = ROOT / ".test-tmp" / f"{name}-{uuid.uuid4().hex[:8]}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "NeoDev Tests"], cwd=root, check=True)
    return root


def _run(script: Path, *args: str, cwd: Path | None = None, input_text: str | None = None, env: dict | None = None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd or ROOT,
        input=input_text,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.stdout
    return json.loads(proc.stdout)


def test_ensure_git_guard_installs_managed_hooks_idempotently():
    repo = _tmp_repo("git-guard-install")
    try:
        first = _run(ENSURE_GUARD, "--repo-root", str(repo), "--json")

        assert first.returncode == 0, first.stderr
        payload = _payload(first)
        assert payload["ok"] is True
        commit_hook = repo / ".git" / "hooks" / "commit-msg"
        pre_push_hook = repo / ".git" / "hooks" / "pre-push"
        assert commit_hook.exists()
        assert pre_push_hook.exists()
        assert "NEODEV-GIT-GUARD" in commit_hook.read_text(encoding="utf-8")
        assert "git_guard_commit_msg.py" in commit_hook.read_text(encoding="utf-8")
        assert "git_guard_pre_push.py" in pre_push_hook.read_text(encoding="utf-8")

        first_commit_content = commit_hook.read_text(encoding="utf-8")
        second = _run(ENSURE_GUARD, "--repo-root", str(repo), "--json")

        assert second.returncode == 0, second.stderr
        assert commit_hook.read_text(encoding="utf-8") == first_commit_content
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_ensure_git_guard_preserves_existing_user_hooks():
    repo = _tmp_repo("git-guard-user-hook")
    try:
        hooks_dir = repo / ".git" / "hooks"
        user_hook = hooks_dir / "commit-msg"
        user_hook.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8", newline="\n")

        proc = _run(ENSURE_GUARD, "--repo-root", str(repo), "--json")

        assert proc.returncode == 0, proc.stderr
        payload = _payload(proc)
        assert payload["chained"][0]["hook"] == "commit-msg"
        preserved = hooks_dir / ".neodev-user-hooks" / "commit-msg"
        assert preserved.exists()
        assert preserved.read_text(encoding="utf-8") == "#!/usr/bin/env sh\nexit 0\n"
        managed = (hooks_dir / "commit-msg").read_text(encoding="utf-8")
        assert "NEODEV-GIT-GUARD" in managed
        assert ".neodev-user-hooks/commit-msg" in managed
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_plugin_hook_command_resolves_script_from_codex_cache_without_source_tree():
    repo = _tmp_repo("git-guard-cache-command")
    codex_home = ROOT / ".test-tmp" / f"codex-home-{uuid.uuid4().hex[:8]}"
    cache_root = codex_home / "plugins" / "cache" / "neodev-local" / "neodev-rd-knowledge" / "9.9.9"
    try:
        cache_root.mkdir(parents=True)
        shutil.copy2(ENSURE_GUARD, cache_root / "ensure_git_guard.py")
        command = _hook_command("ensure_git_guard.py")

        proc = subprocess.run(
            command,
            cwd=repo,
            env={**os.environ, "CODEX_HOME": str(codex_home)},
            text=True,
            capture_output=True,
            shell=True,
            check=False,
        )

        assert proc.returncode == 0, proc.stderr
        payload = _payload(proc)
        assert payload["ok"] is True
        commit_hook = repo / ".git" / "hooks" / "commit-msg"
        assert commit_hook.exists()
        assert str(cache_root).replace("\\", "/") in commit_hook.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        shutil.rmtree(codex_home, ignore_errors=True)


def test_git_guard_commit_msg_rejects_code_commit_without_docchange_id():
    repo = _tmp_repo("git-guard-commit-code")
    try:
        (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
        message_file = repo / "COMMIT_EDITMSG"
        message_file.write_text("feat: missing trailer\n", encoding="utf-8")

        proc = _run(COMMIT_GUARD, str(message_file), cwd=repo)

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["ok"] is False
        assert payload["scope"] == "code"
        assert payload["errors"][0]["message"] == "DocChange-ID trailer is required"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_guard_commit_msg_skips_document_only_commit():
    repo = _tmp_repo("git-guard-commit-doc")
    try:
        doc = repo / "docs" / "requirements" / "example.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Example\n", encoding="utf-8")
        subprocess.run(["git", "add", "docs/requirements/example.md"], cwd=repo, check=True)
        message_file = repo / "COMMIT_EDITMSG"
        message_file.write_text("docs: update requirement\n", encoding="utf-8")

        proc = _run(COMMIT_GUARD, str(message_file), cwd=repo)

        payload = _payload(proc)
        assert proc.returncode == 0
        assert payload["ok"] is True
        assert payload["scope"] == "document"
        assert payload["skipped"] == "document-only commit"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_guard_pre_push_blocks_failed_verify_doc_change():
    repo = _tmp_repo("git-guard-pre-push")
    try:
        (repo / "app.py").write_text("print('push')\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "feat: missing trailer", "--no-verify"], cwd=repo, check=True)
        commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

        stub = repo / "neodev_stub.py"
        calls = repo / "neodev_calls.jsonl"
        stub.write_text(
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(calls)!r}).write_text(json.dumps(sys.argv[1:]) + '\\n', encoding='utf-8')\n"
            "print(json.dumps({'ok': False, 'command': 'git verify-doc-change', 'data': None, 'errors': [{'category': 'invalid_argument', 'message': 'DocChange-ID trailer is required', 'details': {}}]}))\n"
            "raise SystemExit(2)\n",
            encoding="utf-8",
        )
        stdin = f"refs/heads/master {commit_sha} refs/heads/master {'0' * 40}\n"

        proc = _run(
            PRE_PUSH_GUARD,
            "--repo-root",
            str(repo),
            "--project-id",
            "13",
            "--json",
            cwd=repo,
            input_text=stdin,
            env={"NEODEV_CLI": f"{sys.executable} {stub}"},
        )

        payload = _payload(proc)
        assert proc.returncode == 1
        assert payload["ok"] is False
        assert payload["failed_commits"][0]["commit_sha"] == commit_sha
        assert "verify-doc-change" in calls.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(repo, ignore_errors=True)
