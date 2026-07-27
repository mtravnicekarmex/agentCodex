from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

from agent import AgentConfig, WORKSPACE
from agent_profile import Agent, vytvor_agenta
from contract_workflow import ContractStore, MemoryUpdate, parse_json_response


HELP = """
Příkazy:
  /new <téma>       Architect vytvoří nový kontrakt a předá ho programmerovi.
  /work             Programmer převezme nejbližší kontrakt a implementuje jej.
  /review           Architect zkontroluje nejbližší hotovou implementaci.
  /status           Zobrazí všechny kontrakty a jejich stav.
  /inbox <agent>    Zobrazí inbox agenta (architect/programmer).
  /chat <agent>     Přepne běžný chat na architect/programmer.
  /help             Zobrazí nápovědu.
  /exit             Ukončí konzoli.
""".strip()


def main(project_root: Path = WORKSPACE) -> None:
    project_root = project_root.resolve()
    config = AgentConfig.nacti(project_root / ".env")
    store = ContractStore(project_root)

    with ExitStack() as stack:
        architect = stack.enter_context(
            vytvor_agenta("architect", config=config, project_root=project_root)
        )
        programmer = stack.enter_context(
            vytvor_agenta("programmer", config=config, project_root=project_root)
        )
        agents = {"architect": architect, "programmer": programmer}
        active = architect

        print("Agentní konzole je připravena.")
        print(HELP)

        while True:
            try:
                raw = input(f"\n[{active.name}] Vy: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nUkončuji.")
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
                show_inbox(project_root, raw.split(maxsplit=1)[1])
                continue
            if raw.startswith("/chat "):
                name = raw.split(maxsplit=1)[1].strip()
                if name not in agents:
                    print("Neznámý agent. Použijte architect nebo programmer.")
                    continue
                active = agents[name]
                print(f"Aktivní chat: {name}")
                continue
            if raw.startswith("/new "):
                create_contract(architect, store, raw.split(maxsplit=1)[1])
                continue
            if raw == "/work":
                implement_next(programmer, store)
                continue
            if raw == "/review":
                review_next(architect, store)
                continue

            try:
                print(f"\n{active.display_name}:\n{active.poloz_dotaz(raw)}")
            except Exception as error:
                print(f"\nChyba agenta: {error}")


def create_contract(architect: Agent, store: ContractStore, task: str) -> None:
    response = architect.spust_prikaz("create_contract", task=task)
    data = parse_json_response(response)
    contract = store.create_contract(
        title=str(data["title"]),
        points=list(data["points"]),
    )
    print(f"Vytvořen {store.path_for(contract.number).name}")
    print("Předáno agentovi programmer.")


def implement_next(programmer: Agent, store: ContractStore) -> None:
    contract = store.next_for_programmer()
    if contract is None:
        print("Programmer nemá žádný připravený kontrakt.")
        return

    contract = store.claim(contract.number)
    path = store.path_for(contract.number)
    response = programmer.spust_prikaz(
        "implement_contract",
        contract_path=path.relative_to(store.project_root).as_posix(),
        contract_content=path.read_text(encoding="utf-8"),
    )
    data = parse_json_response(response)
    store.record_programmer_result(
        contract.number,
        summary=str(data["summary"]),
        notes=list(data["notes"]),
        tests=list(data.get("tests", [])),
    )
    print(f"CONTRACT {contract.number:04d} je předán architectovi k review.")


def review_next(architect: Agent, store: ContractStore) -> None:
    contract = store.next_for_architect_review()
    if contract is None:
        print("Architect nemá žádný kontrakt připravený k review.")
        return

    path = store.path_for(contract.number)
    response = architect.spust_prikaz(
        "review_contract",
        contract_path=path.relative_to(store.project_root).as_posix(),
        contract_content=path.read_text(encoding="utf-8"),
    )
    data = parse_json_response(response)
    updates = [
        MemoryUpdate(path=str(item["path"]), text=str(item["text"]))
        for item in data.get("memory_updates", [])
    ]
    updated = store.record_architect_review(
        contract.number,
        approved=bool(data["approved"]),
        summary=str(data["summary"]),
        reviews=list(data["reviews"]),
        memory_updates=updates,
    )
    print(
        f"CONTRACT {contract.number:04d}: {updated.status}; "
        f"předáno {updated.handoff_to}."
    )


def print_status(store: ContractStore) -> None:
    contracts = store.list_contracts()
    if not contracts:
        print("Zatím nejsou žádné kontrakty.")
        return
    for contract in contracts:
        print(
            f"CONTRACT {contract.number:04d} | {contract.status:<28} | "
            f"handoff: {contract.handoff_to:<10} | {contract.title}"
        )


def show_inbox(project_root: Path, agent: str) -> None:
    path = project_root / "agents" / agent / "INBOX.md"
    if agent == "owner":
        path = project_root / "contracts" / "OWNER_INBOX.md"
    if not path.is_file():
        print(f"Inbox {agent!r} je prázdný.")
        return
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
