from agent import AgentConfig
from agent_profile import vytvor_agenta


def main() -> None:
    config = AgentConfig.nacti()
    with vytvor_agenta("architect", config=config) as architect:
        odpoved = architect.spust_prikaz(
            "analyze_architecture",
            task="Prověř oddělení vytvor_vlakno() a vytvor_agenta().",
        )
        print(odpoved)


if __name__ == "__main__":
    main()
