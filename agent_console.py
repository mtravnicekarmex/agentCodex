from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

from agent import AgentConfig, WORKSPACE
from agent_profile import Agent, create_agent
from contract_workflow import Contract, ContractStore, MemoryUpdate, parse_json_response
from git_ops import commit_and_push


HELP = """
Commands:
  /new <topic>       Architect creates a new contract (DRAFT). Runs
                      automatically from there: reviewer's architecture
                      review, then (only if ACCEPTED) the programmer's
                      implementation and the architect's implementation
                      review. Stops and reports back once it returns to
                      the architect (APPROVED, CHANGES_REQUESTED,
                      ARCHITECTURE_CHANGES_REQUESTED, or REJECTED).
  /revise <n> <topic> Architect rewrites the requirements of a contract
                      returned by the reviewer (ARCHITECTURE_CHANGES_REQUESTED),
                      resubmits it for review, and continues automatically
                      the same way /new does.
  /work [n]         Manual override: programmer picks up contract <n> (or
                      the next ready one) and implements it. Not needed in
                      the normal flow — /new and /revise already chain this.
  /review [n]       Manual override: architect runs implementation review
                      on contract <n> (or the next ready one). Not needed
                      in the normal flow.
  /commit <n>       After discussing implementation review's result with
                      the architect and agreeing it is sufficient, commits
                      and pushes contract <n> (must be APPROVED).
  /status           Shows all contracts and their status.
  /inbox <agent>    Shows an agent's inbox (architect/reviewer/programmer/owner).
  /chat <agent>     Switches the plain chat to architect/reviewer/programmer.
  /help             Shows this help.
  /exit             Exits the console.
""".strip()

INBOX_AGENTS = ("architect", "reviewer", "programmer", "owner")


def main(project_root: Path = WORKSPACE) -> None:
    project_root = project_root.resolve()
    config = AgentConfig.load(project_root / ".env")
    store = ContractStore(project_root)

    with ExitStack() as stack:
        architect = stack.enter_context(
            create_agent("architect", config=config, project_root=project_root)
        )
        reviewer = stack.enter_context(
            create_agent("reviewer", config=config, project_root=project_root)
        )
        programmer = stack.enter_context(
            create_agent("programmer", config=config, project_root=project_root)
        )
        agents = {"architect": architect, "reviewer": reviewer, "programmer": programmer}
        active = architect

        print("Agent console is ready.")
        print(HELP)

        while True:
            try:
                raw = input(f"\n[{active.name}] You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not raw:
                continue
            if raw == "/exit":
                break
            if raw == "/help":
                print(HELP)
                continue
            if raw == "/status":
                print_status(store)
                continue
            if raw.startswith("/inbox "):
                name = raw.split(maxsplit=1)[1].strip()
                if name not in INBOX_AGENTS:
                    print("Unknown agent. Use architect, reviewer, programmer, or owner.")
                    continue
                show_inbox(project_root, name)
                continue
            if raw.startswith("/chat "):
                name = raw.split(maxsplit=1)[1].strip()
                if name not in agents:
                    print("Unknown agent. Use architect, reviewer, or programmer.")
                    continue
                active = agents[name]
                print(f"Active chat: {name}")
                continue
            if raw.startswith("/new "):
                try:
                    create_contract(
                        architect, reviewer, programmer, store, raw.split(maxsplit=1)[1]
                    )
                except Exception as error:
                    print(f"\nError while creating the contract: {error}")
                continue
            if raw.startswith("/revise "):
                try:
                    _, rest = raw.split(maxsplit=1)
                    number_str, task = rest.split(maxsplit=1)
                    revise_contract(
                        architect, reviewer, programmer, store, int(number_str), task
                    )
                except Exception as error:
                    print(f"\nError while revising the contract: {error}")
                continue
            if raw == "/work" or raw.startswith("/work "):
                try:
                    number = int(raw.split(maxsplit=1)[1]) if " " in raw else None
                    implement_next(programmer, store, number=number)
                except Exception as error:
                    print(f"\nError while implementing the contract: {error}")
                continue
            if raw == "/review" or raw.startswith("/review "):
                try:
                    number = int(raw.split(maxsplit=1)[1]) if " " in raw else None
                    review_next(architect, store, number=number)
                except Exception as error:
                    print(f"\nError while reviewing the contract: {error}")
                continue
            if raw.startswith("/commit "):
                try:
                    commit_approved_contract(store, int(raw.split(maxsplit=1)[1]))
                except Exception as error:
                    print(f"\nError while committing: {error}")
                continue

            try:
                print(f"\n{active.display_name}:\n{active.ask(raw)}")
            except Exception as error:
                print(f"\nAgent error: {error}")


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


if __name__ == "__main__":
    main()
