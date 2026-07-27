from __future__ import annotations

from agent import AgentConfig
from agent_profile import vytvor_agenta


def main() -> None:
    config = AgentConfig.nacti()

    with vytvor_agenta(
        "architect",
        config=config,
    ) as architect:
        print("Architect je připraven.")
        print("Ukončení: /exit")
        print("Nový řádek odešlete klávesou Enter.\n")

        while True:
            try:
                dotaz = input("Vy: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nUkončuji.")
                break

            if not dotaz:
                continue

            if dotaz.lower() in {
                "/exit",
                "/quit",
                "exit",
                "quit",
            }:
                break

            try:
                odpoved = architect.poloz_dotaz(dotaz)
            except Exception as chyba:
                print(f"\nChyba: {chyba}\n")
                continue

            print(f"\nArchitect:\n{odpoved}\n")


if __name__ == "__main__":
    main()