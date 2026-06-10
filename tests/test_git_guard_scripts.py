import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "neodev-rd-knowledge"
CHECK_SCOPE = PLUGIN_ROOT / "check_git_commit_scope.py"


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


def test_plugin_hook_command_resolves_scope_script_from_codex_cache_without_source_tree():
    repo = _tmp_repo("git-guard-cache-command")
    codex_home = ROOT / ".test-tmp" / f"codex-home-{uuid.uuid4().hex[:8]}"
    cache_root = codex_home / "plugins" / "cache" / "neodev-local" / "neodev-rd-knowledge" / "9.9.9"
    try:
        cache_root.mkdir(parents=True)
        shutil.copy2(CHECK_SCOPE, cache_root / "check_git_commit_scope.py")
        command = _hook_command("check_git_commit_scope.py")

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
        assert payload["scope"] == "empty"
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        shutil.rmtree(codex_home, ignore_errors=True)


def test_commit_scope_code_route_points_to_post_push_atomic_hook():
    repo = _tmp_repo("git-guard-scope-code")
    try:
        (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)

        proc = _run(CHECK_SCOPE, cwd=repo)

        payload = _payload(proc)
        assert proc.returncode == 0
        assert payload["scope"] == "code"
        assert "post-push atomic graph update hook" in payload["required_workflow"]
        assert "project refresh-graph after push" not in payload["required_workflow"]
    finally:
        shutil.rmtree(repo, ignore_errors=True)
