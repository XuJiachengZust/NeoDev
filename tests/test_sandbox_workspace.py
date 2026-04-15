"""沙箱工作空间 Backend 和 Middleware 测试。

deepagents.__init__ 会导入 langchain.agents.create_agent，
在没有完整 langchain 环境时会失败。所有 deepagents 导入用 try/except 包裹。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# deepagents 包导入（可能因 langchain 缺失而失败）
try:
    from deepagents.backends.workspace import SandboxWorkspaceBackend
    from deepagents.middleware.workspace import (
        SandboxWorkspaceMiddleware,
        WORKSPACE_ORCHESTRATOR_PROMPT,
        WORKSPACE_SUBAGENT_PROMPT,
        _append_to_system_message,
        _build_orchestrator_prompt,
        _build_subagent_prompt,
    )
    _HAS_DEEPAGENTS = True
except ImportError:
    _HAS_DEEPAGENTS = False

needs_deepagents = pytest.mark.skipif(
    not _HAS_DEEPAGENTS,
    reason="deepagents 依赖不可用（需要 langchain agents）",
)


# ---------------------------------------------------------------------------
# SandboxWorkspaceBackend 测试
# ---------------------------------------------------------------------------

@needs_deepagents
class TestSandboxWorkspaceBackend:
    """Backend 生命周期测试。"""

    def test_creates_tmpdir(self):
        ws = SandboxWorkspaceBackend()
        try:
            assert ws.workspace_path.exists()
            assert ws.workspace_path.is_dir()
        finally:
            ws.cleanup()

    def test_creates_standard_subdirs(self):
        ws = SandboxWorkspaceBackend()
        try:
            assert (ws.workspace_path / "reports").is_dir()
            assert (ws.workspace_path / "artifacts").is_dir()
        finally:
            ws.cleanup()

    def test_custom_base_dir(self, tmp_path):
        ws = SandboxWorkspaceBackend(base_dir=tmp_path)
        try:
            assert ws.workspace_path.parent == tmp_path
        finally:
            ws.cleanup()

    def test_custom_prefix(self):
        ws = SandboxWorkspaceBackend(prefix="test_ws_")
        try:
            assert ws.workspace_path.name.startswith("test_ws_")
        finally:
            ws.cleanup()

    def test_virtual_mode_enabled(self):
        ws = SandboxWorkspaceBackend()
        try:
            assert ws.virtual_mode is True
        finally:
            ws.cleanup()

    def test_cwd_equals_workspace_path(self):
        ws = SandboxWorkspaceBackend()
        try:
            assert ws.cwd == ws.workspace_path
        finally:
            ws.cleanup()

    def test_write_and_read(self):
        ws = SandboxWorkspaceBackend()
        try:
            result = ws.write("/reports/test.md", "# 测试报告\n详细内容")
            assert result.error is None
            assert result.files_update is None  # 不进 state

            content = ws.read("/reports/test.md")
            assert "测试报告" in content
            assert "详细内容" in content
        finally:
            ws.cleanup()

    def test_write_creates_nested_dirs(self):
        ws = SandboxWorkspaceBackend()
        try:
            result = ws.write("/artifacts/deep/nested/file.txt", "content")
            assert result.error is None
            assert (ws.workspace_path / "artifacts" / "deep" / "nested" / "file.txt").exists()
        finally:
            ws.cleanup()

    def test_cleanup_removes_dir(self):
        ws = SandboxWorkspaceBackend()
        path = ws.workspace_path
        ws.cleanup()
        assert not path.exists()

    def test_cleanup_idempotent(self):
        ws = SandboxWorkspaceBackend()
        ws.cleanup()
        ws.cleanup()  # 不应抛出异常

    def test_reset_creates_new_dir(self):
        ws = SandboxWorkspaceBackend()
        try:
            old_path = ws.workspace_path
            ws.write("/reports/old.md", "旧内容")
            ws.reset()
            new_path = ws.workspace_path

            assert not old_path.exists()
            assert new_path.exists()
            assert old_path != new_path
            assert ws.cwd == new_path
        finally:
            ws.cleanup()

    def test_reset_recreates_standard_subdirs(self):
        ws = SandboxWorkspaceBackend()
        try:
            ws.reset()
            assert (ws.workspace_path / "reports").is_dir()
            assert (ws.workspace_path / "artifacts").is_dir()
        finally:
            ws.cleanup()

    def test_reset_clears_old_files(self):
        ws = SandboxWorkspaceBackend()
        try:
            ws.write("/reports/old.md", "旧内容")
            ws.reset()
            content = ws.read("/reports/old.md")
            assert "Error" in content or "not found" in content.lower() or "does not exist" in content.lower()
        finally:
            ws.cleanup()

    def test_path_isolation_blocks_traversal(self):
        ws = SandboxWorkspaceBackend()
        try:
            content = ws.read("/../../../etc/passwd")
            assert "Error" in content or "not found" in content.lower() or "invalid" in content.lower() or "outside" in content.lower()
        finally:
            ws.cleanup()


# ---------------------------------------------------------------------------
# _append_to_system_message 工具函数测试
# ---------------------------------------------------------------------------

@needs_deepagents
class TestAppendToSystemMessage:

    def test_none_input(self):
        result = _append_to_system_message(None, "extra")
        assert result == "extra"

    def test_string_input(self):
        result = _append_to_system_message("base prompt", "extra")
        assert result == "base prompt\n\nextra"

    def test_system_message_input(self):
        from langchain_core.messages import SystemMessage
        msg = SystemMessage(content="base prompt")
        result = _append_to_system_message(msg, "extra")
        assert isinstance(result, SystemMessage)
        blocks = result.content_blocks
        texts = [b["text"] for b in blocks if isinstance(b, dict) and "text" in b]
        assert any("extra" in t for t in texts)


# ---------------------------------------------------------------------------
# SandboxWorkspaceMiddleware 测试
# ---------------------------------------------------------------------------

@needs_deepagents
class TestSandboxWorkspaceMiddleware:

    def test_invalid_role_raises(self):
        ws = SandboxWorkspaceBackend()
        try:
            with pytest.raises(ValueError, match="orchestrator.*subagent"):
                SandboxWorkspaceMiddleware(ws, role="invalid")
        finally:
            ws.cleanup()

    def test_role_property(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="orchestrator")
            assert mw.role == "orchestrator"
            mw2 = SandboxWorkspaceMiddleware(ws, role="subagent")
            assert mw2.role == "subagent"
        finally:
            ws.cleanup()

    def test_workspace_property(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="orchestrator")
            assert mw.workspace is ws
        finally:
            ws.cleanup()

    def test_orchestrator_first_call_no_reset(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="orchestrator")
            ws.write("/reports/keep.md", "应保留")
            path_before = ws.workspace_path

            mw.before_agent({}, MagicMock(), {})

            assert ws.workspace_path == path_before
            content = ws.read("/reports/keep.md")
            assert "应保留" in content
        finally:
            ws.cleanup()

    def test_orchestrator_second_call_resets(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="orchestrator")
            ws.write("/reports/old.md", "旧内容")

            mw.before_agent({}, MagicMock(), {})
            old_path = ws.workspace_path

            mw.before_agent({}, MagicMock(), {})
            assert ws.workspace_path != old_path
            assert not old_path.exists()
        finally:
            ws.cleanup()

    def test_subagent_never_resets(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="subagent")
            ws.write("/reports/data.md", "数据")
            path_before = ws.workspace_path

            mw.before_agent({}, MagicMock(), {})
            mw.before_agent({}, MagicMock(), {})
            mw.before_agent({}, MagicMock(), {})

            assert ws.workspace_path == path_before
            content = ws.read("/reports/data.md")
            assert "数据" in content
        finally:
            ws.cleanup()

    def test_orchestrator_prompt_injected(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="orchestrator")
            captured = {}

            def handler(request):
                captured["system"] = request.system_message
                return MagicMock()

            request = MagicMock()
            request.system_message = "base"
            request.override = lambda system_message: MagicMock(system_message=system_message)

            mw.wrap_model_call(request, handler)
            assert WORKSPACE_ORCHESTRATOR_PROMPT in captured["system"]
        finally:
            ws.cleanup()

    def test_subagent_prompt_injected(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="subagent")
            captured = {}

            def handler(request):
                captured["system"] = request.system_message
                return MagicMock()

            request = MagicMock()
            request.system_message = "base"
            request.override = lambda system_message: MagicMock(system_message=system_message)

            mw.wrap_model_call(request, handler)
            assert WORKSPACE_SUBAGENT_PROMPT in captured["system"]
        finally:
            ws.cleanup()

    def test_before_agent_returns_none(self):
        ws = SandboxWorkspaceBackend()
        try:
            for role in ("orchestrator", "subagent"):
                mw = SandboxWorkspaceMiddleware(ws, role=role)
                result = mw.before_agent({}, MagicMock(), {})
                assert result is None
        finally:
            ws.cleanup()


# ---------------------------------------------------------------------------
# 父子共享工作空间集成测试
# ---------------------------------------------------------------------------

@needs_deepagents
class TestSharedWorkspace:
    """验证父子智能体共享同一磁盘目录。"""

    def test_subagent_writes_orchestrator_reads(self):
        ws = SandboxWorkspaceBackend()
        try:
            ws.write("/reports/analysis.md", "# 分析报告\n发现了3个问题")
            content = ws.read("/reports/analysis.md")
            assert "分析报告" in content
            assert "3个问题" in content
        finally:
            ws.cleanup()

    def test_multiple_subagents_write_different_files(self):
        ws = SandboxWorkspaceBackend()
        try:
            ws.write("/reports/task_a.md", "任务A结果")
            ws.write("/reports/task_b.md", "任务B结果")
            ws.write("/artifacts/data.json", '{"key": "value"}')

            assert "任务A" in ws.read("/reports/task_a.md")
            assert "任务B" in ws.read("/reports/task_b.md")
            assert "key" in ws.read("/artifacts/data.json")
        finally:
            ws.cleanup()


# ---------------------------------------------------------------------------
# 可配置路径前缀测试
# ---------------------------------------------------------------------------

@needs_deepagents
class TestConfigurablePathPrefix:
    """验证 _build_*_prompt 函数和 path_prefix 参数。"""

    def test_build_orchestrator_prompt_default_prefix(self):
        prompt = _build_orchestrator_prompt()
        assert "/workspace/reports/" in prompt
        assert "/workspace/artifacts/" in prompt

    def test_build_orchestrator_prompt_custom_prefix(self):
        prompt = _build_orchestrator_prompt("/workspace/sandbox/")
        assert "/workspace/sandbox/reports/" in prompt
        assert "/workspace/sandbox/artifacts/" in prompt
        assert "/workspace/sandbox/plan.md" in prompt

    def test_build_subagent_prompt_default_prefix(self):
        prompt = _build_subagent_prompt()
        assert "/workspace/reports/" in prompt
        assert "/workspace/artifacts/" in prompt

    def test_build_subagent_prompt_custom_prefix(self):
        prompt = _build_subagent_prompt("/workspace/sandbox/")
        assert "/workspace/sandbox/reports/" in prompt
        assert "/workspace/sandbox/artifacts/" in prompt

    def test_constants_equal_default_prompts(self):
        """向后兼容：常量应等于默认前缀生成的提示词。"""
        assert WORKSPACE_ORCHESTRATOR_PROMPT == _build_orchestrator_prompt()
        assert WORKSPACE_SUBAGENT_PROMPT == _build_subagent_prompt()

    def test_middleware_custom_path_prefix(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="orchestrator", path_prefix="/workspace/sandbox/")
            captured = {}

            def handler(request):
                captured["system"] = request.system_message
                return MagicMock()

            request = MagicMock()
            request.system_message = "base"
            request.override = lambda system_message: MagicMock(system_message=system_message)

            mw.wrap_model_call(request, handler)
            assert "/workspace/sandbox/reports/" in captured["system"]
            assert "/workspace/sandbox/artifacts/" in captured["system"]
        finally:
            ws.cleanup()

    def test_middleware_subagent_custom_path_prefix(self):
        ws = SandboxWorkspaceBackend()
        try:
            mw = SandboxWorkspaceMiddleware(ws, role="subagent", path_prefix="/workspace/sandbox/")
            captured = {}

            def handler(request):
                captured["system"] = request.system_message
                return MagicMock()

            request = MagicMock()
            request.system_message = "base"
            request.override = lambda system_message: MagicMock(system_message=system_message)

            mw.wrap_model_call(request, handler)
            assert "/workspace/sandbox/reports/" in captured["system"]
            assert "/workspace/sandbox/artifacts/" in captured["system"]
        finally:
            ws.cleanup()
