from __future__ import annotations

from pathlib import Path

import pytest

from contract_workflow import ContractStore, MemoryUpdate, parse_json_response


def create_store(tmp_path: Path) -> ContractStore:
    (tmp_path / "agents" / "architect").mkdir(parents=True)
    (tmp_path / "agents" / "programmer").mkdir(parents=True)
    return ContractStore(tmp_path)


def test_contract_full_cycle(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    contract = store.create_contract(
        "Test workflow",
        [
            {
                "assignment": "Přidat funkci.",
                "acceptance_criteria": ["Funkce je testovaná."],
            },
            {
                "assignment": "Doplnit dokumentaci.",
                "acceptance_criteria": ["README obsahuje příklad."],
            },
        ],
    )
    assert contract.number == 1
    assert store.path_for(1).name == "CONTRACT - 0001.md"
    assert store.next_for_programmer() is not None

    store.claim(1)
    store.record_programmer_result(
        1,
        summary="Implementováno.",
        notes=[
            {
                "point": 1,
                "note": "Přidána funkce.",
                "files": ["module.py"],
                "tests": ["pytest — passed"],
            },
            {
                "point": 2,
                "note": "Doplněn README.",
                "files": ["README.md"],
                "tests": [],
            },
        ],
    )

    assert store.next_for_architect_review() is not None
    reviewed = store.record_architect_review(
        1,
        approved=True,
        summary="V pořádku.",
        reviews=[
            {"point": 1, "status": "APPROVED", "review": "Implementace odpovídá."},
            {"point": 2, "status": "APPROVED", "review": "Dokumentace odpovídá."},
        ],
        memory_updates=[
            MemoryUpdate(
                path="memory/DECISIONS.md",
                text="Workflow kontraktů je schválen.",
            )
        ],
    )
    assert reviewed.status == "APPROVED"
    assert reviewed.handoff_to == "owner"
    assert "Workflow kontraktů" in (
        tmp_path / "memory" / "DECISIONS.md"
    ).read_text(encoding="utf-8")


def test_review_requires_every_point(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    store.create_contract(
        "Test",
        [{"assignment": "Bod 1"}, {"assignment": "Bod 2"}],
    )
    store.claim(1)
    store.record_programmer_result(
        1,
        summary="Hotovo.",
        notes=[
            {"point": 1, "note": "A"},
            {"point": 2, "note": "B"},
        ],
    )
    with pytest.raises(ValueError, match="Chybí body: 2"):
        store.record_architect_review(
            1,
            approved=True,
            summary="Review",
            reviews=[
                {"point": 1, "status": "APPROVED", "review": "OK"},
            ],
        )


def test_rejects_unsafe_memory_path(tmp_path: Path) -> None:
    store = create_store(tmp_path)
    with pytest.raises(ValueError, match="Nepovolený cíl"):
        store.append_memory(
            MemoryUpdate(path="../outside.md", text="No"),
            source="TEST",
        )


def test_parse_fenced_json() -> None:
    data = parse_json_response('```json\n{"approved": true}\n```')
    assert data["approved"] is True
