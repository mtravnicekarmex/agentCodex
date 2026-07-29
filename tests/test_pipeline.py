from __future__ import annotations

import json
from pathlib import Path

import pytest

import agents.pipeline as pipeline
from agents.contract_workflow import ContractStore


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
    monkeypatch.setattr(pipeline, "commit_and_push", fake)
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

    pipeline.create_contract(architect, reviewer, programmer, store, "Add X")

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

    pipeline.commit_approved_contract(store, 1)

    assert fake_git.calls == [(tmp_path.resolve(), "CONTRACT_0001 - IMPLEMENTED")]


def test_commit_approved_contract_refuses_when_not_approved(
    tmp_path: Path, fake_git: FakeGit
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])

    pipeline.commit_approved_contract(store, 1)

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

    pipeline.create_contract(architect, reviewer, programmer, store, "Add X")

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

    pipeline.create_contract(architect, reviewer, programmer, store, "Add X")

    contract = store.load(1)
    assert contract.status == "CHANGES_REQUESTED"
    # The chain stops here — a second automatic programmer round must not run.
    assert programmer.calls == ["implement_contract"]


def test_opening_briefing_includes_status_and_inbox(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])

    briefing = pipeline.opening_briefing(store, tmp_path)

    assert "IMPLEMENTATION_CONTRACT_0001" in briefing
    assert "agenda" in briefing.lower()


def test_extract_pipeline_action_returns_none_for_plain_reply() -> None:
    visible, action = pipeline.extract_pipeline_action("Just a normal reply.")

    assert visible == "Just a normal reply."
    assert action is None


def test_extract_pipeline_action_parses_trailing_block() -> None:
    reply = (
        "Sounds good, let's draft it.\n\n"
        '```pipeline-action\n{"action": "create", "task": "Add X"}\n```'
    )

    visible, action = pipeline.extract_pipeline_action(reply)

    assert visible == "Sounds good, let's draft it."
    assert action == {"action": "create", "task": "Add X"}


def test_extract_pipeline_action_ignores_malformed_json() -> None:
    reply = "Ok.\n```pipeline-action\nnot json\n```"

    visible, action = pipeline.extract_pipeline_action(reply)

    assert visible == reply
    assert action is None


def test_extract_pipeline_action_ignores_block_without_action_key() -> None:
    reply = 'Ok.\n```pipeline-action\n{"number": 1}\n```'

    visible, action = pipeline.extract_pipeline_action(reply)

    assert visible == reply
    assert action is None


def test_dispatch_pipeline_action_create_calls_create_contract(
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

    pipeline.dispatch_pipeline_action(
        {"action": "create", "task": "Add X"}, architect, reviewer, programmer, store
    )

    assert architect.calls == ["create_contract"]
    assert store.load(1).title == "Test"


def test_dispatch_pipeline_action_commit_calls_commit_approved_contract(
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

    pipeline.dispatch_pipeline_action(
        {"action": "commit", "number": 1}, None, None, None, store
    )

    assert fake_git.calls == [(tmp_path.resolve(), "CONTRACT_0001 - IMPLEMENTED")]


def test_dispatch_pipeline_action_ignores_unknown_action(tmp_path: Path) -> None:
    store = create_store(tmp_path)

    # Must not raise — an unrecognized action is reported, not acted on.
    pipeline.dispatch_pipeline_action(
        {"action": "delete_everything"}, None, None, None, store
    )


def test_find_stuck_contracts_returns_only_mid_pipeline_statuses(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Stuck at programmer", [{"assignment": "Point 1"}])
    store.record_architecture_review(1, verdict="ACCEPTED", findings="fine")
    store.create_contract("Waiting on owner", [{"assignment": "Point 1"}])
    store.record_architecture_review(
        2, verdict="CHANGES_REQUESTED", findings="needs work"
    )

    stuck = pipeline.find_stuck_contracts(store)

    assert [c.number for c in stuck] == [1]
    assert stuck[0].status == "READY_FOR_PROGRAMMER"


def test_opening_briefing_flags_stuck_contract(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract("Stuck one", [{"assignment": "Point 1"}])
    store.record_architecture_review(1, verdict="ACCEPTED", findings="fine")

    briefing = pipeline.opening_briefing(store, tmp_path)

    assert "IMPLEMENTATION_CONTRACT_0001" in briefing
    assert "resume" in briefing.lower()
    assert "interrupted" in briefing.lower()


def test_opening_briefing_has_no_stuck_note_when_queue_is_clean(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    briefing = pipeline.opening_briefing(store, tmp_path)

    assert "mid-pipeline" not in briefing.lower()


def test_resume_stuck_contract_from_ready_for_programmer_runs_full_chain(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Do X", "acceptance_criteria": ["ok"]}])
    store.record_architecture_review(1, verdict="ACCEPTED", findings="fine")
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
    architect = ScriptedAgent(
        {
            "review_contract": [
                json.dumps(
                    {
                        "approved": True,
                        "summary": "Good",
                        "reviews": [
                            {"point": 1, "status": "APPROVED", "review": "ok"}
                        ],
                    }
                )
            ],
        }
    )

    pipeline.resume_stuck_contract(architect, programmer, store, 1)

    assert store.load(1).status == "APPROVED"
    assert programmer.calls == ["implement_contract"]
    assert architect.calls == ["review_contract"]


def test_resume_stuck_contract_from_ready_for_architect_review(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Do X"}])
    store.record_architecture_review(1, verdict="ACCEPTED", findings="fine")
    store.claim(1)
    store.record_programmer_result(
        1,
        summary="done",
        notes=[{"point": 1, "note": "did it", "files": [], "tests": []}],
    )
    architect = ScriptedAgent(
        {
            "review_contract": [
                json.dumps(
                    {
                        "approved": True,
                        "summary": "Good",
                        "reviews": [
                            {"point": 1, "status": "APPROVED", "review": "ok"}
                        ],
                    }
                )
            ],
        }
    )

    pipeline.resume_stuck_contract(architect, None, store, 1)

    assert store.load(1).status == "APPROVED"
    assert architect.calls == ["review_contract"]


def test_resume_stuck_contract_does_nothing_for_non_stuck_status(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Do X"}])

    # Status is DRAFT — must not raise, and must not touch the contract.
    pipeline.resume_stuck_contract(None, None, store, 1)

    assert store.load(1).status == "DRAFT"


def test_dispatch_pipeline_action_resume_calls_resume_stuck_contract(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Do X"}])
    store.record_architecture_review(1, verdict="ACCEPTED", findings="fine")
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
    architect = ScriptedAgent(
        {
            "review_contract": [
                json.dumps(
                    {
                        "approved": True,
                        "summary": "Good",
                        "reviews": [
                            {"point": 1, "status": "APPROVED", "review": "ok"}
                        ],
                    }
                )
            ],
        }
    )

    pipeline.dispatch_pipeline_action(
        {"action": "resume", "number": 1}, architect, None, programmer, store
    )

    assert store.load(1).status == "APPROVED"


def test_inbox_text_returns_empty_string_when_missing(tmp_path: Path) -> None:
    assert pipeline.inbox_text(tmp_path, "architect") == ""


def test_inbox_text_reads_agent_inbox(tmp_path: Path) -> None:
    inbox = tmp_path / "agents" / "architect"
    inbox.mkdir(parents=True)
    (inbox / "INBOX.md").write_text("hello", encoding="utf-8")

    assert pipeline.inbox_text(tmp_path, "architect") == "hello"


def test_inbox_text_reads_owner_inbox_from_contracts_dir(tmp_path: Path) -> None:
    contracts = tmp_path / "contracts"
    contracts.mkdir(parents=True)
    (contracts / "OWNER_INBOX.md").write_text("owner note", encoding="utf-8")

    assert pipeline.inbox_text(tmp_path, "owner") == "owner note"


def test_role_snapshot_groups_contracts_by_current_handoff(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract("Waiting on reviewer", [{"assignment": "Do X"}])
    store.create_contract("Waiting on programmer", [{"assignment": "Do Y"}])
    store.record_architecture_review(2, verdict="ACCEPTED", findings="fine")

    snapshot = pipeline.role_snapshot(store)

    assert [c.number for c in snapshot["reviewer"]] == [1]
    assert [c.number for c in snapshot["programmer"]] == [2]
    assert snapshot["architect"] == []


def test_role_snapshot_empty_queue_returns_empty_lists_for_every_role(
    tmp_path: Path,
) -> None:
    store = create_store(tmp_path)

    snapshot = pipeline.role_snapshot(store)

    assert snapshot == {"reviewer": [], "architect": [], "programmer": []}
