from __future__ import annotations

import json
from pathlib import Path

import pytest

import agent_console
from contract_workflow import ContractStore


class ScriptedAgent:
    """Minimal stand-in for Agent: only needs .run_command(name, **vars)."""

    def __init__(self, responses: dict[str, list[str]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def run_command(self, command_name: str, **variables: str) -> str:
        self.calls.append(command_name)
        queue = self.responses[command_name]
        return queue.pop(0)


class FakeGit:
    """Stand-in for git_ops.commit_and_push — no real git repo needed."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def __call__(self, project_root: Path, message: str) -> bool:
        self.calls.append((project_root, message))
        return True


@pytest.fixture(autouse=True)
def fake_git(monkeypatch: pytest.MonkeyPatch) -> FakeGit:
    fake = FakeGit()
    monkeypatch.setattr(agent_console, "commit_and_push", fake)
    return fake


def create_store(tmp_path: Path) -> ContractStore:
    (tmp_path / "agents" / "architect").mkdir(parents=True)
    (tmp_path / "agents" / "reviewer").mkdir(parents=True)
    (tmp_path / "agents" / "programmer").mkdir(parents=True)
    return ContractStore(tmp_path)


def test_create_contract_chains_through_to_implementation_review(
    tmp_path: Path, fake_git: FakeGit
) -> None:
    store = create_store(tmp_path)
    architect = ScriptedAgent(
        {
            "create_contract": [
                json.dumps(
                    {
                        "title": "Test",
                        "points": [
                            {"assignment": "Do X", "acceptance_criteria": ["X works"]}
                        ],
                        "purpose": "P",
                    }
                )
            ],
            "review_contract": [
                json.dumps(
                    {
                        "approved": True,
                        "summary": "Good",
                        "reviews": [
                            {"point": 1, "status": "APPROVED", "review": "ok"}
                        ],
                        "memory_updates": [],
                    }
                )
            ],
        }
    )
    reviewer = ScriptedAgent(
        {
            "architecture_review": [
                json.dumps(
                    {"verdict": "ACCEPTED", "findings": "fine", "memory_updates": []}
                )
            ],
        }
    )
    programmer = ScriptedAgent(
        {
            "implement_contract": [
                json.dumps(
                    {
                        "summary": "done",
                        "notes": [
                            {
                                "point": 1,
                                "note": "did it",
                                "files": ["a.py"],
                                "tests": [],
                            }
                        ],
                        "tests": [],
                    }
                )
            ],
        }
    )

    agent_console.create_contract(architect, reviewer, programmer, store, "Add X")

    contract = store.load(1)
    assert contract.status == "APPROVED"
    assert reviewer.calls == ["architecture_review"]
    assert programmer.calls == ["implement_contract"]
    assert architect.calls == ["create_contract", "review_contract"]
    assert fake_git.calls == [(tmp_path.resolve(), "CONTRACT_0001")]


def test_commit_approved_contract_commits_with_implemented_suffix(
    tmp_path: Path, fake_git: FakeGit
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])
    store.record_architecture_review(1, verdict="ACCEPTED", findings="fine")
    store.claim(1)
    store.record_programmer_result(
        1,
        summary="done",
        notes=[{"point": 1, "note": "did it", "files": [], "tests": []}],
    )
    store.record_implementation_review(
        1,
        approved=True,
        summary="good",
        reviews=[{"point": 1, "status": "APPROVED", "review": "ok"}],
    )

    agent_console.commit_approved_contract(store, 1)

    assert fake_git.calls == [(tmp_path.resolve(), "CONTRACT_0001 - IMPLEMENTED")]


def test_commit_approved_contract_refuses_when_not_approved(
    tmp_path: Path, fake_git: FakeGit
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])

    agent_console.commit_approved_contract(store, 1)

    assert fake_git.calls == []


def test_create_contract_stops_when_changes_requested_at_architecture_review(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    architect = ScriptedAgent(
        {
            "create_contract": [
                json.dumps(
                    {
                        "title": "Test",
                        "points": [
                            {"assignment": "Do X", "acceptance_criteria": ["X works"]}
                        ],
                    }
                )
            ],
        }
    )
    reviewer = ScriptedAgent(
        {
            "architecture_review": [
                json.dumps({"verdict": "CHANGES_REQUESTED", "findings": "needs work"})
            ],
        }
    )
    programmer = ScriptedAgent({})

    agent_console.create_contract(architect, reviewer, programmer, store, "Add X")

    contract = store.load(1)
    assert contract.status == "ARCHITECTURE_CHANGES_REQUESTED"
    assert programmer.calls == []


def test_create_contract_stops_after_changes_requested_implementation_review(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    architect = ScriptedAgent(
        {
            "create_contract": [
                json.dumps(
                    {
                        "title": "Test",
                        "points": [
                            {"assignment": "Do X", "acceptance_criteria": ["X works"]}
                        ],
                    }
                )
            ],
            "review_contract": [
                json.dumps(
                    {
                        "approved": False,
                        "summary": "Not quite",
                        "reviews": [
                            {
                                "point": 1,
                                "status": "CHANGES_REQUESTED",
                                "review": "missing test",
                            }
                        ],
                    }
                )
            ],
        }
    )
    reviewer = ScriptedAgent(
        {
            "architecture_review": [
                json.dumps({"verdict": "ACCEPTED", "findings": "fine"})
            ],
        }
    )
    programmer = ScriptedAgent(
        {
            "implement_contract": [
                json.dumps(
                    {
                        "summary": "done",
                        "notes": [
                            {"point": 1, "note": "did it", "files": [], "tests": []}
                        ],
                        "tests": [],
                    }
                )
            ],
        }
    )

    agent_console.create_contract(architect, reviewer, programmer, store, "Add X")

    contract = store.load(1)
    assert contract.status == "CHANGES_REQUESTED"
    # The chain stops here — a second automatic programmer round must not run.
    assert programmer.calls == ["implement_contract"]
