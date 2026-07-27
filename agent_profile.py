from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent import AgentConfig, AgentVlakno, Provider, Reasoning, WORKSPACE, vytvor_vlakno


ProfileLevel = Literal["low", "mid", "high"]


@dataclass(frozen=True)
class AgentProfileConfig:
    name: str
    display_name: str
    provider: Provider
    model_profile: ProfileLevel
    reasoning_profile: ProfileLevel
    permission_profile: str
    persistent_thread: bool = False
    load_private_memory: bool = True
    load_working_state: bool = True
    load_shared_memory: bool = True


class AgentProfile:
    """Načte verzovaný profil jednoho agenta z ``agents/<name>/``."""

    def __init__(self, project_root: Path, agent_name: str) -> None:
        self.project_root = project_root.resolve()
        self.agent_name = self._validate_agent_name(agent_name)
        self.directory = self.project_root / "agents" / self.agent_name
        self.config_file = self.directory / "config.json"
        self.role_file = self.directory / "ROLE.md"
        self.memory_file = self.directory / "MEMORY.md"
        self.working_state_file = self.directory / "WORKING_STATE.md"
        self.commands_file = self.directory / "COMMANDS.md"
        self.commands_directory = self.directory / "commands"
        self.runtime_directory = self.directory / "runtime"
        self.thread_file = self.runtime_directory / "thread.json"
        self.config = self._load_config()

    @staticmethod
    def _validate_agent_name(agent_name: str) -> str:
        normalized = agent_name.strip()
        if not normalized or not re.fullmatch(r"[A-Za-z0-9_-]+", normalized):
            raise ValueError(
                "Název agenta smí obsahovat pouze písmena, číslice, '_' a '-'."
            )
        return normalized

    def _load_config(self) -> AgentProfileConfig:
        data = json.loads(self._read_required(self.config_file))
        required = {
            "name",
            "provider",
            "model_profile",
            "reasoning_profile",
            "permission_profile",
        }
        missing = sorted(required - data.keys())
        if missing:
            raise ValueError(
                f"V {self.config_file} chybí položky: {', '.join(missing)}"
            )
        if data["name"] != self.agent_name:
            raise ValueError(
                f"Jméno v config.json ({data['name']!r}) neodpovídá složce "
                f"agenta ({self.agent_name!r})."
            )

        provider = data["provider"]
        if provider not in ("codex", "claude"):
            raise ValueError(f"Neznámý provider profilu: {provider!r}")

        model_profile = self._validate_level(data["model_profile"], "model_profile")
        reasoning_profile = self._validate_level(
            data["reasoning_profile"], "reasoning_profile"
        )

        return AgentProfileConfig(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            provider=provider,
            model_profile=model_profile,
            reasoning_profile=reasoning_profile,
            permission_profile=data["permission_profile"],
            persistent_thread=bool(data.get("persistent_thread", False)),
            load_private_memory=bool(data.get("load_private_memory", True)),
            load_working_state=bool(data.get("load_working_state", True)),
            load_shared_memory=bool(data.get("load_shared_memory", True)),
        )

    @staticmethod
    def _validate_level(value: str, field_name: str) -> ProfileLevel:
        if value not in ("low", "mid", "high"):
            raise ValueError(
                f"Neplatná hodnota {field_name}: {value!r}. "
                "Povolené hodnoty: low, mid, high."
            )
        return value  # type: ignore[return-value]

    @staticmethod
    def _read_required(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Požadovaný soubor neexistuje: {path}")
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"Soubor je prázdný: {path}")
        return content

    @staticmethod
    def _read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def load_role(self) -> str:
        return self._read_required(self.role_file)

    def load_private_memory(self) -> str:
        return self._read_optional(self.memory_file)

    def load_working_state(self) -> str:
        return self._read_optional(self.working_state_file)

    def load_command(self, command_name: str, **variables: str) -> str:
        command_name = self._validate_agent_name(command_name)
        path = self.commands_directory / f"{command_name}.md"
        template = self._read_required(path)

        for key, value in variables.items():
            template = template.replace("{{" + key.upper() + "}}", value)

        unresolved = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", template)))
        if unresolved:
            raise ValueError(
                f"Příkazu {command_name!r} chybí hodnoty: {', '.join(unresolved)}"
            )
        return template


class Agent:
    """Vyšší agentní objekt: profil + technické konverzační vlákno."""

    def __init__(self, profile: AgentProfile, thread: AgentVlakno) -> None:
        self.profile = profile
        self.thread = thread

    @property
    def name(self) -> str:
        return self.profile.config.name

    @property
    def display_name(self) -> str:
        return self.profile.config.display_name

    @property
    def provider(self) -> Provider:
        return self.profile.config.provider

    @property
    def model(self) -> str:
        return self.thread.model

    @property
    def reasoning(self) -> Reasoning:
        return self.thread.reasoning

    @property
    def permission_profile(self) -> str:
        return self.thread.permission_profile

    def poloz_dotaz(self, text: str) -> str:
        return self.thread.poloz_dotaz(text)

    polož_dotaz = poloz_dotaz

    def spust_prikaz(self, command_name: str, **variables: str) -> str:
        prompt = self.profile.load_command(command_name, **variables)
        return self.thread.poloz_dotaz(prompt)

    def zavri(self) -> None:
        self.thread.zavri()

    def __enter__(self) -> "Agent":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.zavri()


def _resolve_provider(profile_provider: Provider, config: AgentConfig) -> Provider:
    configured = {
        "codex": config.PROVIDER_CODEX,
        "claude": config.PROVIDER_CLAUDE,
    }[profile_provider]
    if configured != profile_provider:
        raise ValueError(
            f"Provider profilu {profile_provider!r} neodpovídá hodnotě v .env "
            f"({configured!r})."
        )
    return profile_provider


def _select_model(config: AgentConfig, provider: Provider, level: ProfileLevel) -> str:
    if provider == "codex":
        mapping = {
            "low": config.MODEL_CODEX_LOW,
            "mid": config.MODEL_CODEX_MID,
            "high": config.MODEL_CODEX_HIGH,
        }
    else:
        mapping = {
            "low": config.MODEL_CLAUDE_LOW,
            "mid": config.MODEL_CLAUDE_MID,
            "high": config.MODEL_CLAUDE_HIGH,
        }
    return mapping[level]


def _select_reasoning(config: AgentConfig, level: ProfileLevel) -> str:
    return {
        "low": config.REASONING_LOW,
        "mid": config.REASONING_MID,
        "high": config.REASONING_HIGH,
    }[level]


def build_agent_instructions(profile: AgentProfile) -> str:
    parts = [profile.load_role()]

    if profile.config.load_private_memory:
        memory = profile.load_private_memory()
        if memory:
            parts.append(
                "# Soukromá dlouhodobá paměť\n\n"
                "Paměť je pomocný kontext; aktuální kód a schválená projektová "
                "rozhodnutí mají přednost.\n\n"
                f"<private_memory>\n{memory}\n</private_memory>"
            )

    if profile.config.load_working_state:
        state = profile.load_working_state()
        if state:
            parts.append(
                "# Aktuální pracovní stav\n\n"
                f"<working_state>\n{state}\n</working_state>"
            )

    if profile.config.load_shared_memory:
        parts.append(
            "# Společná projektová paměť\n\n"
            "Před významnějším úkolem si podle relevance přečti soubory v "
            "adresáři `memory/`, zejména `PROJECT_STATE.md`, `DECISIONS.md` "
            "a `OPEN_TASKS.md`. Aktuální zdrojový kód má přednost před starou "
            "pamětí."
        )

    parts.append(
        "# Technický profil\n\n"
        f"- Agent: `{profile.config.name}`\n"
        f"- Provider: `{profile.config.provider}`\n"
        f"- Oprávnění: `{profile.config.permission_profile}`\n"
        f"- Kořen projektu: `{profile.project_root}`\n\n"
        "Pracuj nad celým projektem. Neomezuj se pouze na svou podsložku "
        "v `agents/`. Technické omezení sandboxu má vždy přednost před textovou "
        "instrukcí."
    )
    return "\n\n".join(parts)


def vytvor_agenta(
    agent_name: str,
    *,
    config: AgentConfig | None = None,
    project_root: Path = WORKSPACE,
) -> Agent:
    """Načte ``agents/<name>/`` a vytvoří nakonfigurovaného agenta."""
    if config is None:
        config = AgentConfig.nacti(project_root / ".env")

    profile = AgentProfile(project_root=project_root, agent_name=agent_name)
    provider = _resolve_provider(profile.config.provider, config)
    model = _select_model(config, provider, profile.config.model_profile)
    reasoning = _select_reasoning(config, profile.config.reasoning_profile)
    instructions = build_agent_instructions(profile)

    thread = vytvor_vlakno(
        provider=provider,
        model=model,
        reasoning=reasoning,
        permission_profile=profile.config.permission_profile,
        config=config,
        instructions=instructions,
    )
    return Agent(profile=profile, thread=thread)
