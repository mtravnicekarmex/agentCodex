from __future__ import annotations

import json
import re
from pathlib import Path

from .agent_profile import Agent
from .contract_workflow import Contract, ContractStore, MemoryUpdate, parse_json_response
from .git_ops import commit_and_push


_PIPELINE_ACTION_RE = re.compile(
    r"```pipeline-action\s*\n(?P<body>.*?)\n?```\s*$", re.DOTALL
)


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
        f"handed off to {contract.handoff_to}.\n"
        f"{data['findings']}"
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
    print(
        f"IMPLEMENTATION_CONTRACT_{contract.number:04d} handed off to the "
        f"architect for review.\n"
        f"{data['summary']}"
    )
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
        f"handed off to {updated.handoff_to}.\n"
        f"{data['summary']}"
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


def extract_pipeline_action(reply: str) -> tuple[str, dict | None]:
    """Splits a trailing ```pipeline-action fenced JSON block off an
    architect reply, if present (see ADR-025 — lets ordinary conversation
    trigger the pipeline instead of requiring the owner to know slash
    commands).

    Returns (visible_text, action): `visible_text` is what the owner
    should actually see (the block removed, trailing whitespace trimmed);
    `action` is the parsed dict, or None if no valid block was found — in
    which case `visible_text` is the original reply, unchanged.
    """
    match = _PIPELINE_ACTION_RE.search(reply)
    if not match:
        return reply, None
    try:
        action = json.loads(match.group("body"))
    except json.JSONDecodeError:
        return reply, None
    if not isinstance(action, dict) or "action" not in action:
        return reply, None
    return reply[: match.start()].rstrip(), action


def dispatch_pipeline_action(
    action: dict,
    architect: Agent,
    reviewer: Agent,
    programmer: Agent,
    store: ContractStore,
) -> None:
    """Acts on a parsed `pipeline-action` block — the conversational
    equivalent of typing `/new`, `/revise`, `/commit`, or `/work` (see
    ADR-025, ADR-026).
    """
    kind = action.get("action")
    if kind == "create":
        create_contract(architect, reviewer, programmer, store, str(action["task"]))
    elif kind == "revise":
        revise_contract(
            architect,
            reviewer,
            programmer,
            store,
            int(action["number"]),
            str(action["task"]),
        )
    elif kind == "commit":
        commit_approved_contract(store, int(action["number"]))
    elif kind == "resume":
        resume_stuck_contract(architect, programmer, store, int(action["number"]))
    else:
        print(f"(Unrecognized pipeline action {kind!r} from the architect — ignored.)")


def find_stuck_contracts(store: ContractStore) -> list[Contract]:
    """Contracts that are mid-pipeline, waiting on an agent turn rather
    than an owner decision (see ADR-026).

    `READY_FOR_PROGRAMMER` and `READY_FOR_ARCHITECT_REVIEW` are always
    meant to be transient — normally `continue_pipeline()` carries a
    contract straight through them in one call. If a contract is still
    sitting in one of these when a new session starts, the process that
    was supposed to carry it forward never finished (e.g. it died
    mid-call), not that anyone is waiting on the owner. Genuine
    owner-facing checkpoints (`APPROVED`, `CHANGES_REQUESTED`,
    `ARCHITECTURE_CHANGES_REQUESTED`, `REJECTED`) are not included here.
    """
    stuck_statuses = {"READY_FOR_PROGRAMMER", "READY_FOR_ARCHITECT_REVIEW"}
    return [c for c in store.list_contracts() if c.status in stuck_statuses]


def resume_stuck_contract(
    architect: Agent, programmer: Agent, store: ContractStore, number: int
) -> None:
    """Continues a contract left mid-pipeline by an interrupted previous
    session (see ADR-026) — picks up wherever `continue_pipeline()` would
    have been, using the same `implement_next`/`review_next` steps.
    """
    contract = store.load(number)
    if contract.status == "READY_FOR_PROGRAMMER":
        implemented = implement_next(programmer, store, number=number)
        if implemented is None:
            return
        review_next(architect, store, number=implemented.number)
    elif contract.status == "READY_FOR_ARCHITECT_REVIEW":
        review_next(architect, store, number=number)
    else:
        print(
            f"IMPLEMENTATION_CONTRACT_{number:04d} is not mid-pipeline "
            f"(status: {contract.status}); nothing to resume."
        )


def opening_briefing(store: ContractStore, project_root: Path) -> str:
    """Builds the first message sent to the architect when a session starts.

    Grounds the greeting in the actual contract queue and the architect's
    own inbox, rather than letting the model guess what might be pending
    (see agents/PRINCIPLES.md P4/P6 and ADR-021). Also flags any contract stuck
    mid-pipeline from an interrupted previous session (see ADR-026), so
    the architect asks the owner about resuming it instead of leaving
    them to notice and dig it out themselves.
    """
    inbox_path = project_root / "agents" / "architect" / "INBOX.md"
    inbox_text = (
        inbox_path.read_text(encoding="utf-8").strip()
        if inbox_path.is_file()
        else ""
    )
    stuck = find_stuck_contracts(store)
    stuck_note = (
        (
            "\n\nThe following contracts are still sitting mid-pipeline "
            "(waiting on programmer or implementation review) — this "
            "normally never survives past one turn, so a previous session "
            "was very likely interrupted (e.g. a restart) before it could "
            "finish. Mention this explicitly and ask the owner whether to "
            "resume; only emit a `pipeline-action` with `\"action\": "
            "\"resume\"` once they say yes:\n"
            + "\n".join(
                f"IMPLEMENTATION_CONTRACT_{c.number:04d}: {c.status} — {c.title}"
                for c in stuck
            )
        )
        if stuck
        else ""
    )
    return (
        "The owner just started a new session with you. Greet them, briefly "
        "mention anything in the contract queue or your inbox that needs "
        "attention, and ask what is on the agenda today.\n\n"
        f"Current contract queue:\n{status_text(store)}\n\n"
        f"Your inbox:\n{inbox_text or '(empty)'}"
        f"{stuck_note}"
    )
