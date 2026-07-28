from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

from agents.agent import AgentConfig, WORKSPACE
from agents.agent_profile import create_agent
from agents.contract_workflow import ContractStore
from agents.pipeline import (
    commit_approved_contract,
    create_contract,
    implement_next,
    opening_briefing,
    revise_contract,
    review_next,
    print_status,
    show_inbox,
)


HELP = """
Talk to the architect directly — plain text goes straight to them.

Commands available alongside the conversation:
  /new <topic>       drafts a new contract; the pipeline then runs on its
                      own (architecture review, and if accepted,
                      implementation and implementation review) and stops
                      once it returns to the architect
  /revise <n> <topic> rewrites contract <n>'s requirements after
                      CHANGES_REQUESTED and continues the same way
  /work [n]         manual override: programmer picks up contract <n> (or
                      the next ready one)
  /review [n]       manual override: architect runs implementation review
                      on contract <n> (or the next ready one)
  /commit <n>       after agreeing the implementation is sufficient,
                      commits and pushes contract <n> (must be APPROVED)
  /status           shows the contract queue
  /inbox            shows the architect's inbox
  /help             shows this help
  /exit             exits
""".strip()


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

        try:
            greeting = architect.ask(opening_briefing(store, project_root))
            print(f"\nArchitect:\n{greeting}\n")
        except Exception as error:
            print(f"\nCould not reach the architect for the opening greeting: {error}\n")

        print("(/help for commands, /exit to quit)\n")

        while True:
            try:
                raw = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not raw:
                continue
            if raw in {"/exit", "/quit", "exit", "quit"}:
                break
            if raw == "/help":
                print(HELP)
                continue
            if raw == "/status":
                print_status(store)
                continue
            if raw == "/inbox":
                show_inbox(project_root, "architect")
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
                print(f"\nArchitect:\n{architect.ask(raw)}\n")
            except Exception as error:
                print(f"\nError: {error}\n")


if __name__ == "__main__":
    main()
