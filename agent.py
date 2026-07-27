from __future__ import annotations

import asyncio
import json
import os
import platform
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeAlias

import claude_agent_sdk
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, TextBlock
from dotenv import load_dotenv
from openai_codex import ApprovalMode, Codex, Sandbox


WORKSPACE = Path(__file__).parent.resolve()

PROVIDERS = ("codex", "claude")
CODEX_REASONING = ("low", "medium", "high")
CLAUDE_REASONING = ("low", "medium", "high")
ALL_REASONING = tuple(dict.fromkeys((*CODEX_REASONING, *CLAUDE_REASONING)))
PERMISSION_PROFILES = ("review", "edit", "full")
Provider = Literal["codex", "claude"]
Reasoning: TypeAlias = Literal["low", "medium", "high"]
PermissionProfile: TypeAlias = Literal["review", "edit", "full"]

PERMISSION_REVIEW: PermissionProfile = "review"
PERMISSION_EDIT: PermissionProfile = "edit"
PERMISSION_FULL: PermissionProfile = "full"

CLAUDE_REVIEW_TOOLS = ("Read", "Grep", "Glob")
CLAUDE_EDIT_TOOLS = (*CLAUDE_REVIEW_TOOLS, "Edit", "Write")
CLAUDE_FULL_TOOLS = (*CLAUDE_EDIT_TOOLS, "Bash")


def _env(klic: str) -> str:
    hodnota = os.environ.get(klic)
    if not hodnota:
        raise RuntimeError(f"V .env chybí hodnota {klic}.")
    return hodnota.strip()


@dataclass(frozen=True)
class AgentConfig:
    """
    Konfigurace nactena z .env. Import modulu sam o sobe .env nenacita.
    """

    PROVIDER_CODEX: str
    PROVIDER_CLAUDE: str
    MODEL_CODEX_LOW: str
    MODEL_CODEX_MID: str
    MODEL_CODEX_HIGH: str
    MODEL_CLAUDE_LOW: str
    MODEL_CLAUDE_MID: str
    MODEL_CLAUDE_HIGH: str
    REASONING_LOW: str
    REASONING_MID: str
    REASONING_HIGH: str

    @classmethod
    def nacti(cls, cesta_env: Path = WORKSPACE / ".env") -> "AgentConfig":
        load_dotenv(cesta_env)
        config = cls(
            PROVIDER_CODEX=_env("PROVIDER_CODEX"),
            PROVIDER_CLAUDE=_env("PROVIDER_CLAUDE"),
            MODEL_CODEX_LOW=_env("MODEL_CODEX_LOW"),
            MODEL_CODEX_MID=_env("MODEL_CODEX_MID"),
            MODEL_CODEX_HIGH=_env("MODEL_CODEX_HIGH"),
            MODEL_CLAUDE_LOW=_env("MODEL_CLAUDE_LOW"),
            MODEL_CLAUDE_MID=_env("MODEL_CLAUDE_MID"),
            MODEL_CLAUDE_HIGH=_env("MODEL_CLAUDE_HIGH"),
            REASONING_LOW=_env("REASONING_LOW"),
            REASONING_MID=_env("REASONING_MID"),
            REASONING_HIGH=_env("REASONING_HIGH"),
        )
        config.over()
        return config

    def over(self) -> None:
        _over_provider(self.PROVIDER_CODEX)
        _over_provider(self.PROVIDER_CLAUDE)
        for reasoning in (self.REASONING_LOW, self.REASONING_MID, self.REASONING_HIGH):
            _over_reasoning(reasoning)

    def modely_pro(self, provider: Provider) -> tuple[str, ...]:
        if provider == "codex":
            return (self.MODEL_CODEX_LOW, self.MODEL_CODEX_MID, self.MODEL_CODEX_HIGH)
        return (self.MODEL_CLAUDE_LOW, self.MODEL_CLAUDE_MID, self.MODEL_CLAUDE_HIGH)

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
    permission_profile: PermissionProfile

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
    if reasoning not in ALL_REASONING:
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


def _over_permission_profile(permission_profile: str) -> PermissionProfile:
    """
    Overi jednotny profil opravneni pro Codex i Claude vlakna.
    """
    if permission_profile not in PERMISSION_PROFILES:
        hodnoty = ", ".join(PERMISSION_PROFILES)
        raise ValueError(
            f"Neznámý profil oprávnění: {permission_profile!r}. "
            f"Povolené hodnoty: {hodnoty}."
        )
    return permission_profile


def _codex_opravneni(permission_profile: PermissionProfile) -> tuple[ApprovalMode, Sandbox]:
    """
    Prevede jednotny profil opravneni na Codex approval/sandbox nastaveni.
    """
    if permission_profile == "review":
        return ApprovalMode.deny_all, Sandbox.read_only
    if permission_profile == "edit":
        return ApprovalMode.deny_all, Sandbox.workspace_write
    return ApprovalMode.deny_all, Sandbox.full_access


def _claude_opravneni(permission_profile: PermissionProfile) -> tuple[list[str], list[str], str]:
    """
    Prevede jednotny profil opravneni na Claude tools/allowed_tools/permission_mode.
    """
    if permission_profile == "review":
        tools = CLAUDE_REVIEW_TOOLS
    elif permission_profile == "edit":
        tools = CLAUDE_EDIT_TOOLS
    else:
        tools = CLAUDE_FULL_TOOLS

    return list(tools), list(tools), "dontAsk"


def _over_model(model: str | None) -> str:
    """
    Overi, ze volajici predal model nacteny z .env.
    """
    if model:
        return model.strip()
    raise RuntimeError("Model není zadaný. Použijte některou z MODEL_* hodnot z .env.")


def _over_model_pro_provider(provider: Provider, model: str, config: AgentConfig) -> None:
    """
    Overi, ze model patri ke zvolenemu provideru podle .env konfigurace.
    """
    povolene = tuple(dict.fromkeys(config.modely_pro(provider)))
    if model not in povolene:
        hodnoty = ", ".join(povolene)
        raise ValueError(
            f"Model {model!r} není podporovaný pro {provider}. "
            f"Povolené hodnoty z .env: {hodnoty}."
        )


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


def _spusti_claude_cli(*args: str, capture_output: bool = False) -> subprocess.CompletedProcess:
    """
    Spusti pribalene `claude` CLI a chybu chybejici binarky prevede na srozumitelnou hlasku.
    """
    try:
        return subprocess.run(
            [str(CLAUDE_BIN), *args],
            capture_output=capture_output,
            text=capture_output,
            check=False,
        )
    except OSError as chyba:
        raise RuntimeError(
            f"Přibalené `claude` CLI se nepodařilo spustit na cestě {CLAUDE_BIN}: {chyba}"
        ) from chyba


def prihlaseni_claude() -> None:
    """
    Zajistí přihlášení do Anthropic účtu (Claude Pro/Max), pokud ještě chybí.

    Claude Agent SDK na rozdíl od Codex SDK nemá vlastní přihlašovací API,
    proto se stav ověřuje a přihlášení spouští přímo přes přibalené `claude` CLI.
    """
    status = _spusti_claude_cli("auth", "status", "--json", capture_output=True)

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
    result = _spusti_claude_cli("auth", "login", "--claudeai")

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

    def __init__(
        self,
        model: str,
        reasoning: Reasoning,
        permission_profile: PermissionProfile,
        approval_mode: ApprovalMode,
        sandbox: Sandbox,
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self.permission_profile = permission_profile
        self._lock = threading.Lock()
        self._zavreno = False
        self._codex = Codex()
        try:
            prihlaseni(self._codex)

            self._thread = self._codex.thread_start(
                approval_mode=approval_mode,
                cwd=str(WORKSPACE),
                model=model,
                config={"model_reasoning_effort": reasoning},
                sandbox=sandbox,
            )
        except Exception:
            self._codex.close()
            raise

        print("\nNové Codex vlákno bylo založeno:")
        print(f"  ID vlákna: {self._thread.id}")
        print(f"  Model:     {model}")
        print(f"  Reasoning: {reasoning}")
        print(f"  Práva:     {permission_profile}")
        print(f"  Sandbox:   {sandbox.value}")
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
        permission_profile: PermissionProfile,
        tools: list[str],
        allowed_tools: list[str],
        reasoning: Reasoning = "medium",
        permission_mode: str = "dontAsk",
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self.permission_profile = permission_profile
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
            tools=tools,
            allowed_tools=allowed_tools,
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
        print(f"  Práva:   {permission_profile}")
        print(f"  Tools:   {', '.join(tools)}")
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
    permission_profile: str,
    *,
    config: AgentConfig | None = None,
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

        permission_profile:
            Jednotny profil opravneni: "review", "edit" nebo "full".

    Vrácený objekt lze používat i jako context manager:

        config = AgentConfig.nacti()
        with vytvor_vlakno(
            config.PROVIDER_CODEX,
            config.MODEL_CODEX_LOW,
            config.REASONING_LOW,
            PERMISSION_REVIEW,
            config=config,
        ) as vlakno:
            print(vlakno.poloz_dotaz("Over tenhle diff."))
    """
    if config is None:
        config = AgentConfig.nacti()

    provider = _over_provider(provider)
    model = _over_model(model)
    reasoning = _over_reasoning(reasoning)
    permission_profile = _over_permission_profile(permission_profile)
    _over_reasoning_pro_provider(provider, reasoning)
    _over_model_pro_provider(provider, model, config)

    if provider == "codex":
        approval_mode, sandbox = _codex_opravneni(permission_profile)
        return CodexVlakno(
            model,
            reasoning=reasoning,
            permission_profile=permission_profile,
            approval_mode=approval_mode,
            sandbox=sandbox,
        )

    tools, allowed_tools, permission_mode = _claude_opravneni(permission_profile)
    return ClaudeVlakno(
        model,
        permission_profile=permission_profile,
        tools=tools,
        allowed_tools=allowed_tools,
        reasoning=reasoning,
        permission_mode=permission_mode,
    )


def main() -> None:
    AgentConfig.nacti()
    inicializuj_prihlaseni()
    print("Přihlášení je připravené. Vlákna zakládejte z kódu přes vytvor_vlakno().")


if __name__ == "__main__":
    main()
