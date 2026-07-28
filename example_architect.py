from agent import AgentConfig
from agent_profile import create_agent


def main() -> None:
    config = AgentConfig.load()
    with create_agent("architect", config=config) as architect:
        answer = architect.run_command(
            "analyze_architecture",
            task="Review the separation between create_thread() and create_agent().",
        )
        print(answer)


if __name__ == "__main__":
    main()
