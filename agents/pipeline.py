from __future__ import annotations

from pathlib import Path

from .agent_profile import Agent
from .contract_workflow import Contract, ContractStore, MemoryUpdate, parse_json_response
from .git_ops import commit_and_push


def create_contract(
    architect: Agent,
    reviewer: Agent,
    programmer: Agent,
    store: ContractStore,
    task: str,
) -> None:
    response = architect.run_command("create_contract", task=task)
    data = parse_json_response(response)
    contract = store.create_contract(
        title=str(data["title"]),
        points=list(data["points"]),
        purpose=str(data.get("purpose", "")),
        intent=str(data.get("intent", "")),
        current_state=str(data.get("current_state", "")),
        inputs=str(data.get("inputs", "")),
        outputs=str(data.get("outputs", "")),
        out_of_scope=str(data.get("out_of_scope", "")),
        future_evolution=str(data.get("future_evolution", "")),
    )
    print(f"Created {store.path_for(contract.number).name} (DRAFT)")
    reviewed = run_architecture_review(reviewer, store, contract.number)
    continue_pipeline(architect, programmer, store, reviewed)


def revise_contract(
    architect: Agent,
    reviewer: Agent,
    programmer: Agent,
    store: ContractStore,
    number: int,
    task: str,
) -> None:
    response = architect.run_command("create_contract", task=task)
    data = parse_json_response(response)
    store.revise_contract(
        number,
        title=str(data["title"]),
        points=list(data["points"]),
        purpose=str(data.get("purpose", "")),
        intent=str(data.get("intent", "")),
        current_state=str(data.get("current_state", "")),
        inputs=str(data.get("inputs", "")),
        outputs=str(data.get("outputs", "")),
        out_of_scope=str(data.get("out_of_scope", "")),
        future_evolution=str(data.get("future_evolution", "")),
    )
    print(f"IMPLEMENTATION_CONTRACT_{number:04d} rewritten (DRAFT).")
    reviewed = run_architecture_review(reviewer, store, number)
    continue_pipeline(architect, programmer, store, reviewed)


def continue_pipeline(
    architect: Agent, programmer: Agent, store: ContractStore, contract: Contract
) -> None:
    """Chains the automatic part of the pipeline after architecture review.

    Only proceeds if the contract passed architecture review
    (READY_FOR_PROGRAMMER). CHANGES_REQUESTED and REJECTED already stop at
    the architect/owner — nothing to chain. Commits the approved contract
    (see ADR-019), then runs the programmer, then the architect's
    implementation review, and stops there regardless of verdict (APPROVED
    or CHANGES_REQUESTED) — every return to the architect is a checkpoint
    for the owner, not a place to keep looping automatically (see
    ADR-018).
    """
    if contract.status != "READY_FOR_PROGRAMMER":
        return

    committed = commit_and_push(
        store.project_root, f"CONTRACT_{contract.number:04d}"
    )
    print(
        f"Committed and pushed: CONTRACT_{contract.number:04d}"
        if committed
        else "Nothing to commit before implementation."
    )

    implemented = implement_next(programmer, store, number=contract.number)
    if implemented is None:
        return
    review_next(architect, store, number=implemented.number)


def commit_approved_contract(store: ContractStore, number: int) -> None:
    contract = store.load(number)
    if contract.status != "APPROVED":
        print(
            f"IMPLEMENTATION_CONTRACT_{number:04d} is not APPROVED "
            f"(status: {contract.status}); not committing."
        )
        return
    committed = commit_and_push(
        store.project_root, f"CONTRACT_{number:04d} - IMPLEMENTED"
    )
    print(
        f"Committed and pushed: CONTRACT_{number:04d} - IMPLEMENTED"
        if committed
        else "Nothing to commit."
    )


def run_architecture_review(reviewer: Agent, store: ContractStore, number: int) -> Contract:
    path = store.path_for(number)
    response = reviewer.run_command(
        "architecture_review",
        contract_path=path.relative_to(store.project_root).as_posix(),
        contract_content=path.read_text(encoding="utf-8"),
    )
    data = parse_json_response(response)
    updates = [
        MemoryUpdate(path=str(item["path"]), text=str(item["text"]))
        for item in data.get("memory_updates", [])
    ]
    contract = store.record_architecture_review(
        number,
        verdict=str(data["verdict"]),
        findings=str(data["findings"]),
        memory_updates=updates,
    )
    print(
        f"Architecture review: {contract.status}; "
        f"handed off to {contract.handoff_to}."
    )
    return contract


def implement_next(
    programmer: Agent, store: ContractStore, *, number: int | None = None
) -> Contract | None:
    if number is None:
        queued = store.next_for_programmer()
        if queued is None:
            print("Programmer has no contract ready.")
            return None
        number = queued.number

    contract = store.claim(number)
    path = store.path_for(contract.number)
    response = programmer.run_command(
        "implement_contract",
        contract_path=path.relative_to(store.project_root).as_posix(),
        contract_content=path.read_text(encoding="utf-8"),
    )
    data = parse_json_response(response)
    contract = store.record_programmer_result(
        contract.number,
        summary=str(data["summary"]),
        notes=list(data["notes"]),
        tests=list(data.get("tests", [])),
    )
    print(f"IMPLEMENTATION_CONTRACT_{contract.number:04d} handed off to the architect for review.")
    return contract


def review_next(
    architect: Agent, store: ContractStore, *, number: int | None = None
) -> Contract | None:
    if number is None:
        queued = store.next_for_implementation_review()
        if queued is None:
            print("Architect has no contract ready for implementation review.")
            return None
        number = queued.number

    path = store.path_for(number)
    response = architect.run_command(
        "review_contract",
        contract_path=path.relative_to(store.project_root).as_posix(),
        contract_content=path.read_text(encoding="utf-8"),
    )
    data = parse_json_response(response)
    updates = [
        MemoryUpdate(path=str(item["path"]), text=str(item["text"]))
        for item in data.get("memory_updates", [])
    ]
    updated = store.record_implementation_review(
        number,
        approved=bool(data["approved"]),
        summary=str(data["summary"]),
        reviews=list(data["reviews"]),
        memory_updates=updates,
    )
    print(
        f"IMPLEMENTATION_CONTRACT_{number:04d}: {updated.status}; "
        f"handed off to {updated.handoff_to}."
    )
    return updated


def print_status(store: ContractStore) -> None:
    contracts = store.list_contracts()
    if not contracts:
        print("No contracts yet.")
        return
    for contract in contracts:
        print(
            f"IMPLEMENTATION_CONTRACT_{contract.number:04d} | {contract.status:<28} | "
            f"handoff: {contract.handoff_to:<10} | {contract.title}"
        )


def show_inbox(project_root: Path, agent: str) -> None:
    path = project_root / "agents" / agent / "INBOX.md"
    if agent == "owner":
        path = project_root / "contracts" / "OWNER_INBOX.md"
    if not path.is_file():
        print(f"Inbox {agent!r} is empty.")
        return
    print(path.read_text(encoding="utf-8"))


def status_text(store: ContractStore) -> str:
    """Plain-text contract queue, for grounding the architect's opening
    greeting in real data instead of a guess (see ADR-021)."""
    contracts = store.list_contracts()
    if not contracts:
        return "No contracts yet."
    return "\n".join(
        f"IMPLEMENTATION_CONTRACT_{c.number:04d}: {c.status} "
        f"(handed off to {c.handoff_to}) — {c.title}"
        for c in contracts
    )


def opening_briefing(store: ContractStore, project_root: Path) -> str:
    """Builds the first message sent to the architect when a session starts.

    Grounds the greeting in the actual contract queue and the architect's
    own inbox, rather than letting the model guess what might be pending
    (see PRINCIPLES.md P4/P6 and ADR-021).
    """
    inbox_path = project_root / "agents" / "architect" / "INBOX.md"
    inbox_text = (
        inbox_path.read_text(encoding="utf-8").strip()
        if inbox_path.is_file()
        else ""
    )
    return (
        "The owner just started a new session with you. Greet them, briefly "
        "mention anything in the contract queue or your inbox that needs "
        "attention, and ask what is on the agenda today.\n\n"
        f"Current contract queue:\n{status_text(store)}\n\n"
        f"Your inbox:\n{inbox_text or '(empty)'}"
    )
