from __future__ import annotations

import json
from pathlib import Path

import pytest

import agent_profile
from agent import AgentConfig
from agent_profile import AgentProfile, build_agent_instructions, vytvor_agenta


def create_profile(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    directory = root / "agents" / "architect"
    commands = directory / "commands"
    commands.mkdir(parents=True)

    (directory / "config.json").write_text(
        json.dumps(
            {
                "name": "architect",
                "provider": "codex",
                "model_profile": "high",
                "reasoning_profile": "high",
                "permission_profile": "review",
            }
        ),
        encoding="utf-8",
    )
    (directory / "ROLE.md").write_text("# Role\nArchitect", encoding="utf-8")
    (directory / "MEMORY.md").write_text("Known decision", encoding="utf-8")
    (directory / "WORKING_STATE.md").write_text("Current task", encoding="utf-8")
    (commands / "review.md").write_text("Review: {{TASK}}", encoding="utf-8")
    return root


def test_profile_loads_files(tmp_path: Path) -> None:
    root = create_profile(tmp_path)
    profile = AgentProfile(root, "architect")

    assert profile.config.provider == "codex"
    assert profile.config.model_profile == "high"
    assert profile.load_role().startswith("# Role")
    assert profile.load_command("review", task="API") == "Review: API"


def test_unresolved_command_variable_fails(tmp_path: Path) -> None:
    root = create_profile(tmp_path)
    profile = AgentProfile(root, "architect")

    with pytest.raises(ValueError, match="TASK"):
        profile.load_command("review")


def test_instructions_include_role_and_memory(tmp_path: Path) -> None:
    root = create_profile(tmp_path)
    profile = AgentProfile(root, "architect")
    instructions = build_agent_instructions(profile)

    assert "Architect" in instructions
    assert "Known decision" in instructions
    assert "Current task" in instructions
    assert "Společná projektová paměť" in instructions


def test_invalid_permission_profile_fails_early(tmp_path: Path) -> None:
    root = create_profile(tmp_path)
    config_file = root / "agents" / "architect" / "config.json"
    data = json.loads(config_file.read_text(encoding="utf-8"))
    data["permission_profile"] = "invalid"
    config_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="permission_profile"):
        AgentProfile(root, "architect")


def test_vytvor_agenta_passes_project_root_as_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = create_profile(tmp_path)
    captured: dict[str, object] = {}

    class FakeThread:
        model = "test-model"
        reasoning = "high"
        permission_profile = "review"

        def poloz_dotaz(self, text: str) -> str:
            return text

        def zavri(self) -> None:
            return None

    def fake_vytvor_vlakno(*args, **kwargs):
        captured.update(kwargs)
        return FakeThread()

    monkeypatch.setattr(agent_profile, "vytvor_vlakno", fake_vytvor_vlakno)

    config = AgentConfig(
        PROVIDER_CODEX="codex",
        PROVIDER_CLAUDE="claude",
        MODEL_CODEX_LOW="codex-low",
        MODEL_CODEX_MID="codex-mid",
        MODEL_CODEX_HIGH="codex-high",
        MODEL_CLAUDE_LOW="claude-low",
        MODEL_CLAUDE_MID="claude-mid",
        MODEL_CLAUDE_HIGH="claude-high",
        REASONING_LOW="low",
        REASONING_MID="medium",
        REASONING_HIGH="high",
    )

    agent = vytvor_agenta("architect", config=config, project_root=root)

    assert captured["cwd"] == root.resolve()
    assert captured["permission_profile"] == "review"
    assert captured["model"] == "codex-high"
    assert "Architect" in str(captured["instructions"])
    agent.zavri()
