from __future__ import annotations

from pathlib import Path

import pytest

from agents.contract_workflow import ContractStore, MemoryUpdate, parse_json_response


def create_store(tmp_path: Path) -> ContractStore:
    (tmp_path / "agents" / "architect").mkdir(parents=True)
    (tmp_path / "agents" / "reviewer").mkdir(parents=True)
    (tmp_path / "agents" / "programmer").mkdir(parents=True)
    return ContractStore(tmp_path)


def test_contract_full_cycle(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    contract = store.create_contract(
        "Test workflow",
        [
            {
                "assignment": "Add a feature.",
                "acceptance_criteria": ["The feature is tested."],
            },
            {
                "assignment": "Update the documentation.",
                "acceptance_criteria": ["README contains an example."],
            },
        ],
        purpose="Verify the contract cycle.",
    )
    assert contract.number == 1
    assert contract.status == "DRAFT"
    assert contract.handoff_to == "reviewer"
    assert store.path_for(1).name == "IMPLEMENTATION_CONTRACT_0001.md"
    assert store.next_for_architecture_review() is not None
    assert store.next_for_programmer() is None

    reviewed_draft = store.record_architecture_review(
        1,
        verdict="ACCEPTED",
        findings="Requirements match AGENTS.md, points are actionable in order.",
    )
    assert reviewed_draft.status == "READY_FOR_PROGRAMMER"
    assert reviewed_draft.handoff_to == "programmer"
    assert len(reviewed_draft.architecture_review_rounds) == 1
    assert store.next_for_programmer() is not None

    store.claim(1)
    store.record_programmer_result(
        1,
        summary="Implemented.",
        notes=[
            {
                "point": 1,
                "note": "Feature added.",
                "files": ["module.py"],
                "tests": ["pytest — passed"],
            },
            {
                "point": 2,
                "note": "README updated.",
                "files": ["README.md"],
                "tests": [],
            },
        ],
    )

    assert store.next_for_implementation_review() is not None
    reviewed = store.record_implementation_review(
        1,
        approved=True,
        summary="Looks good.",
        reviews=[
            {"point": 1, "status": "APPROVED", "review": "Implementation matches."},
            {"point": 2, "status": "APPROVED", "review": "Documentation matches."},
        ],
        memory_updates=[
            MemoryUpdate(
                path="memory/DECISIONS.md",
                text="Contract workflow is approved.",
            )
        ],
    )
    assert reviewed.status == "APPROVED"
    assert reviewed.handoff_to == "owner"
    assert len(reviewed.implementation_review_rounds) == 1
    assert "Contract workflow" in (
        tmp_path / "memory" / "DECISIONS.md"
    ).read_text(encoding="utf-8")


def test_architecture_review_accepts_memory_updates(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])
    store.record_architecture_review(
        1,
        verdict="ACCEPTED",
        findings="Requirements are actionable.",
        memory_updates=[
            MemoryUpdate(
                path="memory/DECISIONS.md",
                text="Found during architecture review: recurring risk worth tracking.",
            )
        ],
    )
    assert "recurring risk worth tracking" in (
        tmp_path / "memory" / "DECISIONS.md"
    ).read_text(encoding="utf-8")


def test_architecture_review_changes_requested_allows_revision(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])
    changed = store.record_architecture_review(
        1,
        verdict="CHANGES_REQUESTED",
        findings="Point 1 has no verifiable criterion.",
    )
    assert changed.status == "ARCHITECTURE_CHANGES_REQUESTED"
    assert changed.handoff_to == "architect"
    assert store.next_for_revision() is not None
    assert store.next_for_architecture_review() is None

    revised = store.revise_contract(
        1,
        title="Test (revised)",
        points=[
            {"assignment": "Point 1", "acceptance_criteria": ["Tests pass."]},
        ],
    )
    assert revised.status == "DRAFT"
    assert revised.handoff_to == "reviewer"
    # The architecture review round history is never cleared, even after revision.
    assert len(revised.architecture_review_rounds) == 1

    accepted = store.record_architecture_review(
        1, verdict="ACCEPTED", findings="Criterion added, looks good."
    )
    assert accepted.status == "READY_FOR_PROGRAMMER"
    assert len(accepted.architecture_review_rounds) == 2


def test_cannot_claim_before_architecture_review(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract("Test", [{"assignment": "Point 1"}])
    with pytest.raises(ValueError, match="handed off to agent 'reviewer'"):
        store.claim(1)


def test_review_requires_every_point(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract(
        "Test",
        [{"assignment": "Point 1"}, {"assignment": "Point 2"}],
    )
    store.record_architecture_review(1, verdict="ACCEPTED", findings="OK")
    store.claim(1)
    store.record_programmer_result(
        1,
        summary="Done.",
        notes=[
            {"point": 1, "note": "A"},
            {"point": 2, "note": "B"},
        ],
    )
    with pytest.raises(ValueError, match="Missing points: 2"):
        store.record_implementation_review(
            1,
            approved=True,
            summary="Review",
            reviews=[
                {"point": 1, "status": "APPROVED", "review": "OK"},
            ],
        )


def test_rejects_unsafe_memory_path(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    with pytest.raises(ValueError, match="Disallowed memory target"):
        store.append_memory(
            MemoryUpdate(path="../outside.md", text="No"),
            source="TEST",
        )


def test_allows_principles_memory_target(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    path = store.append_memory(
        MemoryUpdate(path="PRINCIPLES.md", text="Review flag: P6 — example."),
        source="architect",
    )
    assert path == (tmp_path / "PRINCIPLES.md").resolve()
    assert "Review flag: P6" in path.read_text(encoding="utf-8")


def test_parse_fenced_json() -> None:
    data = parse_json_response('```json\n{"approved": true}\n```')
    assert data["approved"] is True
