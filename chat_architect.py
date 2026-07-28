from __future__ import annotations

from agent import AgentConfig
from agent_profile import create_agent


def main() -> None:
    config = AgentConfig.load()

    with create_agent(
        "architect",
        config=config,
    ) as architect:
        print("Architect is ready.")
        print("Exit: /exit")
        print("Press Enter to send a new line.\n")

        while True:
            try:
                question = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not question:
                continue

            if question.lower() in {
                "/exit",
                "/quit",
                "exit",
                "quit",
            }:
                break

            try:
                answer = architect.ask(question)
            except Exception as error:
                print(f"\nError: {error}\n")
                continue

            print(f"\nArchitect:\n{answer}\n")


if __name__ == "__main__":
    main()
