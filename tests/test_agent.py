from __future__ import annotations

import subprocess

import pytest

import agents.agent as agent


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["claude"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_login_claude_returns_when_already_logged_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        agent,
        "_run_claude_cli",
        lambda *args, **kwargs: _completed(0, stdout='{"loggedIn": true}'),
    )

    agent.login_claude()


def test_login_claude_triggers_login_flow_on_nonzero_exit_with_valid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The real `claude auth status --json` exits non-zero when the user is
    # not logged in, while still printing valid JSON with `loggedIn: false`
    # — this must trigger the login flow, not be treated as a failed check.
    calls: list[tuple[str, ...]] = []

    def fake_run(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(args)
        if args[:2] == ("auth", "status"):
            return _completed(
                1, stdout='{"loggedIn": false, "authMethod": "none"}'
            )
        if args[:2] == ("auth", "login"):
            return _completed(0)
        raise AssertionError(f"unexpected call: {args}")

    monkeypatch.setattr(agent, "_run_claude_cli", fake_run)

    agent.login_claude()

    assert ("auth", "status", "--json") in calls
    assert ("auth", "login", "--claudeai") in calls


def test_login_claude_raises_when_status_output_is_not_parseable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        agent,
        "_run_claude_cli",
        lambda *args, **kwargs: _completed(1, stderr="unexpected crash"),
    )

    with pytest.raises(RuntimeError, match="Could not verify Claude login status"):
        agent.login_claude()


def test_login_claude_raises_when_login_flow_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
        if args[:2] == ("auth", "status"):
            return _completed(1, stdout='{"loggedIn": false}')
        if args[:2] == ("auth", "login"):
            return _completed(1)
        raise AssertionError(f"unexpected call: {args}")

    monkeypatch.setattr(agent, "_run_claude_cli", fake_run)

    with pytest.raises(RuntimeError, match="Login to the Anthropic account failed"):
        agent.login_claude()
