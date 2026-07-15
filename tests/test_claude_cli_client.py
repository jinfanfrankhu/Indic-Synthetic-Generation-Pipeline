"""`claude-cli` teacher: shells out to the local Claude Code CLI.

These tests never spawn the real CLI — they pin the factory wiring and the
command construction, which is where the breakage would be.
"""
from __future__ import annotations

import pytest

from syndata.client import ClaudeCliClient, MockClient, build_client


def test_build_client_returns_cli_client_without_any_api_key():
    # The point of this teacher: no PROVIDERS entry, no *_API_KEY needed.
    client = build_client("claude-cli")
    assert isinstance(client, ClaudeCliClient)


def test_model_alias_is_parsed_from_the_id():
    assert build_client("claude-cli:opus")._model_alias == "opus"
    assert build_client("claude-cli")._model_alias == "sonnet"  # default


def test_shared_call_site_kwargs_are_absorbed():
    # generate-drip / bootstrap-seeds pass these to every teacher; the CLI has no
    # equivalent, so it must not blow up on them.
    client = build_client("claude-cli:sonnet", calls_per_minute=12, max_retries=1)
    assert isinstance(client, ClaudeCliClient)


def test_mock_still_wins():
    assert isinstance(build_client("mock"), MockClient)


def test_complete_builds_a_headless_no_tool_command(monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = '[{"prompt": "x", "expected": "y"}]'
        stderr = ""

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return _Proc()

    import subprocess
    monkeypatch.setattr(subprocess, "run", fake_run)

    out = ClaudeCliClient("opus").complete(
        model="claude-cli:opus", system="SYS", user="USR",
        temperature=1.0, max_tokens=256,
    )
    assert out == '[{"prompt": "x", "expected": "y"}]'
    cmd = seen["cmd"]
    assert cmd[:3] == ["claude", "-p", "USR"]
    assert "--model" in cmd and cmd[cmd.index("--model") + 1] == "opus"
    assert cmd[cmd.index("--append-system-prompt") + 1] == "SYS"
    # Tools off: a permission prompt would hang a non-interactive run.
    assert "--disallowed-tools" in cmd
    assert "Bash" in cmd[cmd.index("--disallowed-tools") + 1]


def test_nonzero_exit_raises_with_stderr_tail(monkeypatch):
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "boom: not logged in"

    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Proc())

    with pytest.raises(RuntimeError, match="boom: not logged in"):
        ClaudeCliClient().complete(
            model="claude-cli", system="s", user="u", temperature=1.0, max_tokens=8,
        )
