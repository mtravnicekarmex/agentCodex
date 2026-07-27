from __future__ import annotations

import asyncio
import json
import os
import platform
import subprocess
import threading
from pathlib import Path
from typing import Literal, Protocol, TypeAlias

import claude_agent_sdk
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, TextBlock
from dotenv import load_dotenv
from openai_codex import ApprovalMode, Codex, Sandbox


WORKSPACE = Path(__file__).parent.resolve()

load_dotenv(WORKSPACE / ".env")

PROVIDERS = ("codex", "claude")
CODEX_REASONING = ("low", "medium", "high")
CLAUDE_REASONING = ("low", "medium", "high")
Provider = Literal["codex", "claude"]
Reasoning: TypeAlias = Literal["low", "medium", "high"]


def _env(klic: str) -> str:
    hodnota = os.environ.get(klic)
    if not hodnota:
        raise RuntimeError(f"V .env chybí hodnota {klic}.")
    return hodnota.strip()


PROVIDER_CODEX = _env("PROVIDER_CODEX")
PROVIDER_CLAUDE = _env("PROVIDER_CLAUDE")

MODEL_CODEX_LOW = _env("MODEL_CODEX_LOW")
MODEL_CODEX_MID = _env("MODEL_CODEX_MID")
MODEL_CODEX_HIGH = _env("MODEL_CODEX_HIGH")
MODEL_CLAUDE_LOW = _env("MODEL_CLAUDE_LOW")
MODEL_CLAUDE_MID = _env("MODEL_CLAUDE_MID")
MODEL_CLAUDE_HIGH = _env("MODEL_CLAUDE_HIGH")

REASONING_LOW = _env("REASONING_LOW")
REASONING_MID = _env("REASONING_MID")
REASONING_HIGH = _env("REASONING_HIGH")

CLAUDE_BIN = (
    Path(claude_agent_sdk.__file__).parent
    / "_bundled"
    / ("claude.exe" if platform.system() == "Windows" else "claude")
)


class AgentVlakno(Protocol):
    """
    Spolecne sync rozhrani pro dlouho zijici konverzacni vlakno.
    """

    nazev: str
    model: str
    reasoning: Reasoning

    def poloz_dotaz(self, text: str) -> str:
        ...

    def zavri(self) -> None:
        ...


def _over_provider(provider: str) -> Provider:
    """
    Overi poskytovatele z verejneho API.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Neznámý poskytovatel: {provider!r}")
    return provider


def _over_reasoning(reasoning: str) -> Reasoning:
    """
    Overi obecnou reasoning uroven z verejneho API.
    """
    if reasoning not in CODEX_REASONING:
        raise ValueError(f"Neznámá reasoning úroveň: {reasoning!r}")
    return reasoning


def _over_reasoning_pro_provider(provider: Provider, reasoning: Reasoning) -> None:
    """
    Overi, ze reasoning uroven podporuje konkretni provider.
    """
    povolene = CODEX_REASONING if provider == "codex" else CLAUDE_REASONING
    if reasoning not in povolene:
        hodnoty = ", ".join(povolene)
        raise ValueError(
            f"Reasoning {reasoning!r} není podporovaný pro {provider}. "
            f"Povolené hodnoty: {hodnoty}."
        )


def _over_model(model: str | None) -> str:
    """
    Overi, ze volajici predal model nacteny z .env.
    """
    if model:
        return model.strip()
    raise RuntimeError("Model není zadaný. Použijte některou z MODEL_* hodnot z .env.")


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


def prihlaseni_claude() -> None:
    """
    Zajistí přihlášení do Anthropic účtu (Claude Pro/Max), pokud ještě chybí.

    Claude Agent SDK na rozdíl od Codex SDK nemá vlastní přihlašovací API,
    proto se stav ověřuje a přihlášení spouští přímo přes přibalené `claude` CLI.
    """
    status = subprocess.run(
        [str(CLAUDE_BIN), "auth", "status", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    if status.returncode != 0:
        detail = (status.stderr or status.stdout or "").strip()
        if detail:
            raise RuntimeError(f"Stav přihlášení Claude nejde ověřit: {detail}")
        raise RuntimeError("Stav přihlášení Claude nejde ověřit.")

    try:
        info = json.loads(status.stdout or "{}")
    except json.JSONDecodeError:
        info = {}

    if info.get("loggedIn"):
        return

    print("Otevřete prohlížeč a přihlaste se do Anthropic účtu...")
    result = subprocess.run([str(CLAUDE_BIN), "auth", "login", "--claudeai"], check=False)

    if result.returncode != 0:
        raise RuntimeError("Přihlášení do Anthropic účtu se nezdařilo.")

    print("Přihlášení bylo úspěšné.")


def inicializuj_prihlaseni(provider: Provider | None = None) -> None:
    """
    Provede jediny povoleny interaktivni krok aplikace: prihlaseni provideru.

    Po uspesnem prihlaseni uz vytvareni vlaken a posilani dotazu nevyzaduje
    zadny vstup z terminalu. Kdyz provider neni zadan, overi se Codex i Claude.
    """
    if provider is not None:
        provider = _over_provider(provider)

    if provider is None or provider == "codex":
        codex = Codex()
        try:
            prihlaseni(codex)
        finally:
            codex.close()

    if provider is None or provider == "claude":
        prihlaseni_claude()


class CodexVlakno:
    """
    Codex vlákno vybraného modelu a reasoning úrovně.

    Nabízí stejné rozhraní (`polož_dotaz`/`zavri`) jako `ClaudeVlakno`, takže
    volající kód nemusí řešit, s jakým poskytovatelem zrovna mluví.
    """

    nazev = "Codex"

    def __init__(self, model: str, reasoning: Reasoning) -> None:
        self.model = model
        self.reasoning = reasoning
        self._lock = threading.Lock()
        self._zavreno = False
        self._codex = Codex()
        prihlaseni(self._codex)

        self._thread = self._codex.thread_start(
            approval_mode=ApprovalMode.deny_all,
            cwd=str(WORKSPACE),
            model=model,
            config={"model_reasoning_effort": reasoning},
            sandbox=Sandbox.workspace_write,
        )

        print("\nNové Codex vlákno bylo založeno:")
        print(f"  ID vlákna: {self._thread.id}")
        print(f"  Model:     {model}")
        print(f"  Reasoning: {reasoning}")
        print(f"  Projekt:   {WORKSPACE}\n")

    def poloz_dotaz(self, text: str) -> str:
        if self._zavreno:
            raise RuntimeError("Codex vlákno je zavřené.")

        with self._lock:
            result = self._thread.run(text)
        return result.final_response or ""

    polož_dotaz = poloz_dotaz

    def zavri(self) -> None:
        if self._zavreno:
            return
        self._zavreno = True
        self._codex.close()

    def __enter__(self) -> "CodexVlakno":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.zavri()


class ClaudeVlakno:
    """
    Claude vlákno vybraného modelu se sync rozhraním nad async ClaudeSDKClient.

    ClaudeSDKClient je čistě asynchronní a musí zůstat připojený mezi
    jednotlivými dotazy (drží konverzační kontext), proto si tato třída
    běží vlastní event loop na pozadí a async volání do něj jen posílá.
    """

    nazev = "Claude"

    def __init__(
        self,
        model: str,
        reasoning: Reasoning = "medium",
        permission_mode: str = "dontAsk",
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self._lock = threading.Lock()
        self._zavreno = False
        prihlaseni_claude()

        self._loop = asyncio.new_event_loop()
        loop_bezi = threading.Event()

        def _spustit_loop() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop.call_soon(loop_bezi.set)
            self._loop.run_forever()

        self._vlakno = threading.Thread(target=_spustit_loop, daemon=True)
        self._vlakno.start()
        loop_bezi.wait()

        options = ClaudeAgentOptions(
            cwd=str(WORKSPACE),
            model=model,
            effort=reasoning,
            permission_mode=permission_mode,
        )
        self._client = ClaudeSDKClient(options)
        try:
            self._spusti(self._client.connect())
        except Exception:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._vlakno.join(timeout=2)
            raise

        print("\nNové Claude vlákno bylo založeno:")
        print(f"  Model:   {model}")
        print(f"  Effort:  {reasoning}")
        print(f"  Projekt: {WORKSPACE}\n")

    def _spusti(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def poloz_dotaz(self, text: str) -> str:
        if self._zavreno:
            raise RuntimeError("Claude vlákno je zavřené.")

        with self._lock:
            return self._spusti(self._poloz_dotaz_async(text))

    polož_dotaz = poloz_dotaz

    async def _poloz_dotaz_async(self, text: str) -> str:
        await self._client.query(text)

        casti: list[str] = []
        async for message in self._client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        casti.append(block.text)

        return "\n".join(casti)

    def zavri(self) -> None:
        if self._zavreno:
            return
        self._zavreno = True
        self._spusti(self._client.disconnect())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._vlakno.join(timeout=2)

    def __enter__(self) -> "ClaudeVlakno":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.zavri()


def vytvor_vlakno(
    provider: str,
    model: str,
    reasoning: str,
    *,
    permission_mode: str = "dontAsk",
) -> CodexVlakno | ClaudeVlakno:
    """
    Zalozi dlouho zijici vlakno pro volani z kodu.

    Args:
        provider:
            Hodnota z PROVIDER_CODEX nebo PROVIDER_CLAUDE.

        model:
            Hodnota z MODEL_CODEX_LOW, MODEL_CODEX_MID, MODEL_CODEX_HIGH,
            MODEL_CLAUDE_LOW, MODEL_CLAUDE_MID nebo MODEL_CLAUDE_HIGH.

        reasoning:
            Hodnota z REASONING_LOW, REASONING_MID nebo REASONING_HIGH.
            Claude SDK stejnou hodnotu pouzije jako effort.

        permission_mode:
            Permission mode pro Claude SDK. Vychozi "dontAsk" se nikdy nepta
            na potvrzeni a neschvalene akce odmitne.

    Vrácený objekt lze používat i jako context manager:

        with vytvor_vlakno(PROVIDER_CODEX, MODEL_CODEX_LOW, REASONING_LOW) as vlakno:
            print(vlakno.poloz_dotaz("Over tenhle diff."))
    """
    provider = _over_provider(provider)
    model = _over_model(model)
    reasoning = _over_reasoning(reasoning)
    _over_reasoning_pro_provider(provider, reasoning)

    if provider == "codex":
        return CodexVlakno(model, reasoning=reasoning)

    return ClaudeVlakno(model, reasoning=reasoning, permission_mode=permission_mode)


def main() -> None:
    inicializuj_prihlaseni()
    print("Přihlášení je připravené. Vlákna zakládejte z kódu přes vytvor_vlakno().")


if __name__ == "__main__":
    main()
