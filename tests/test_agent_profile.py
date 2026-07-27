from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_profile import AgentProfile, build_agent_instructions


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
