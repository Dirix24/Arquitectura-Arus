import subprocess
from unittest.mock import Mock, patch

import pytest

from ai.ollama_process import OllamaProcess
from security.path_guard import PathGuard
from tools.shell_tool import ShellTool
from tools.tool_manager import ToolManager


def test_shell_preserves_safe_operations_without_launching_process(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    shell = ShellTool()
    with patch("subprocess.Popen", side_effect=AssertionError("unexpected process")):
        assert shell.execute("echo safe") == "safe"
        assert shell.execute("cat hello.txt") == "hello"
        assert "hello.txt" in shell.execute("ls")
        assert shell.execute("unknown").startswith("ERROR")
        assert shell.execute("").startswith("ERROR")


def test_workspace_rejects_symlinks_and_large_reads(tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    (workspace / "outside-link").symlink_to(outside)
    (workspace / "dir-link").symlink_to(tmp_path, target_is_directory=True)
    (workspace / "large").write_bytes(b"x" * (256 * 1024 + 1))
    guard = PathGuard(workspace)
    for path in ("../outside.txt", "outside-link", "dir-link/outside.txt", "large"):
        with pytest.raises((ValueError, OSError)):
            guard.read(path)
    with pytest.raises((ValueError, OSError)):
        guard.write("dir-link/outside.txt", "new")
    assert outside.read_text(encoding="utf-8") == "private"
    guard.write("sub/allowed.txt", "new")
    guard.write("sub/allowed.txt", "updated")
    assert guard.read("sub/allowed.txt") == "updated"


def test_model_dispatcher_defaults_to_read_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = ToolManager()
    assert manager.execute("calculator", expression="2 + 2") == "4"
    assert manager.execute("calculator", expression="2 ** 100").startswith("Error")
    assert manager.execute("file", action="write", path="test", content="blocked").startswith("ERROR")
    assert manager.execute("file", action="read", path=["wrong type"]).startswith("ERROR")
    assert not (tmp_path / "test").exists()
    for name in ("run_tests", "github_clone", "file_writer"):
        assert manager.execute(name).startswith("ERROR")
    assert {item["function"]["name"] for item in manager.schemas()} == {"time", "calculator", "shell", "file"}


def test_ollama_existing_listener_is_never_started_or_stopped():
    manager = OllamaProcess()
    with patch("ai.ollama_process.socket.create_connection"), patch("ai.ollama_process.subprocess.Popen") as popen:
        assert manager.start() == "existing"
        manager.stop()
        popen.assert_not_called()
    with pytest.raises(ValueError):
        manager.start("https://example.org")


def test_ollama_only_manages_its_own_child():
    manager = OllamaProcess()
    child = Mock()
    child.poll.return_value = None
    child.wait.side_effect = [subprocess.TimeoutExpired("ollama", 2), 0]
    with (
        patch("ai.ollama_process.socket.create_connection", side_effect=ConnectionRefusedError),
        patch("ai.ollama_process.subprocess.Popen", return_value=child) as popen,
    ):
        assert manager.start("http://127.0.0.1:11435") == "started"
        assert popen.call_args.kwargs["env"]["OLLAMA_HOST"] == "127.0.0.1:11435"
        assert manager.start("http://127.0.0.1:11435") == "owned"
        manager.stop()
        manager.stop()
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
