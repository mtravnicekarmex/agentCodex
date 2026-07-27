from __future__ import annotations

from pathlib import Path

from openai_codex import Codex, Sandbox, Thread



WORKSPACE = Path(__file__).parent.resolve()



def prihlaseni(codex: Codex) -> None:
    """
    Zajistí přihlášení přes účet ChatGPT, pokud ještě chybí.

    SDK umí znovu použít existující Codex autentizaci automaticky,
    takže interaktivní login spustíme jen při prvním použití nebo po odhlášení.
    """
    account = codex.account(refresh_token=True)

    if account.account is not None:
        return

    if not account.requires_openai_auth:
        return

    login = codex.login_chatgpt()

    print("Otevřete tuto adresu v prohlížeči:")
    print(login.auth_url)

    result = login.wait()

    if not result.success:
        raise RuntimeError(
            f"Přihlášení přes ChatGPT se nezdařilo: {result.error or 'neznámá chyba'}."
        )

    account = codex.account(refresh_token=True)
    if account.account is None:
        raise RuntimeError("Přihlášení doběhlo, ale aktivní účet stále není k dispozici.")

    print("Přihlášení bylo úspěšné.")




def new_thread(
    codex: Codex,
    model: str,
    reasoning: str,
) -> Thread:
    """
    Založí nové Codex vlákno.

    Args:
        codex:
            Aktivní instance Codex SDK.

        model:
            ID modelu, například "gpt-5.4".

        reasoning:
            Úroveň přemýšlení modelu, například:
            "low", "medium", "high" nebo "xhigh".

    Returns:
        Nově založené Codex vlákno.
    """

    thread = codex.thread_start(
        cwd=str(WORKSPACE),
        model=model,
        config={
            "model_reasoning_effort": reasoning,
        },
        sandbox=Sandbox.workspace_write,
    )

    print("\nNové vlákno bylo založeno:")
    print(f"  ID vlákna: {thread.id}")
    print(f"  Model:     {model}")
    print(f"  Reasoning: {reasoning}")
    print(f"  Projekt:   {WORKSPACE}\n")

    return thread


def run_chat(thread: Thread) -> None:
    """
    Spustí interaktivní chat v již založeném vlákně.
    """

    print("Chat je spuštěný.")
    print("Pro ukončení napište 'konec'.\n")

    while True:
        try:
            prompt = input("Vy: ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nChat byl ukončen.")
            break

        if prompt.lower() in {"konec", "exit", "quit"}:
            print("Chat byl ukončen.")
            break

        if not prompt:
            continue

        try:
            result = thread.run(prompt)

            print("\nCodex:")
            print(result.final_response or "[Codex nevrátil textovou odpověď]")
            print()

        except Exception as exc:
            print(f"\nChyba při zpracování dotazu: {exc}\n")





def main() -> None:
    with Codex() as codex:
        prihlaseni(codex)
        thread = new_thread(
            codex=codex,
            model="gpt-5.4",
            reasoning="medium",
        )

        run_chat(thread)




if __name__ == "__main__":
    main()
