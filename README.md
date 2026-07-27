# agentCodex

Tenká vrstva nad [Codex SDK](https://github.com/openai/codex) a [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Oba providery zpřístupňuje přes stejné synchronní rozhraní: dlouho žijící konverzační vlákno, kterému postupně pokládáte dotazy a ono si mezi nimi drží kontext.

Celý běhový kód je v [`agent.py`](agent.py). Doporučené skladby agentů jsou v [`AGENTS_SUGGESTIONS.md`](AGENTS_SUGGESTIONS.md).

## Instalace

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Zkopírujte `.env.example` do `.env` a upravte modely podle účtů, které používáte:

```bash
cp .env.example .env
```

```dotenv
PROVIDER_CODEX=codex
PROVIDER_CLAUDE=claude

MODEL_CODEX_LOW=gpt-5.4
MODEL_CODEX_MID=gpt-5.4
MODEL_CODEX_HIGH=gpt-5.4

MODEL_CLAUDE_LOW=claude-haiku-4-5-20251001
MODEL_CLAUDE_MID=claude-sonnet-5
MODEL_CLAUDE_HIGH=claude-opus-4-8

REASONING_LOW=low
REASONING_MID=medium
REASONING_HIGH=high
```

`.env` se nenačítá při importu modulu. Načítá se explicitně přes `AgentConfig.nacti()`.

## Přihlášení

Přihlášení je jediný povolený interaktivní krok. Spusťte:

```bash
python agent.py
```

Tím se ověří nebo založí přihlášení pro oba providery:

- Codex přes ChatGPT účet.
- Claude přes přibalené `claude auth login --claudeai`.

Po prvním úspěšném přihlášení už vytváření vláken a dotazy nevyžadují ruční potvrzení.

## Základní použití

Nejdřív načtěte konfiguraci:

```python
from agent import AgentConfig

config = AgentConfig.nacti()
```

Vlákno se zakládá jedinou funkcí:

```python
vytvor_vlakno(provider, model, reasoning, permission_profile, config=config)
```

### Review vlákno

```python
from agent import AgentConfig, PERMISSION_REVIEW, vytvor_vlakno

config = AgentConfig.nacti()

with vytvor_vlakno(
    config.PROVIDER_CODEX,
    config.MODEL_CODEX_LOW,
    config.REASONING_LOW,
    PERMISSION_REVIEW,
    config=config,
) as agent:
    print(agent.poloz_dotaz("Udělej revizi souboru agent.py."))
```

### Edit vlákno

```python
from agent import AgentConfig, PERMISSION_EDIT, vytvor_vlakno

config = AgentConfig.nacti()

with vytvor_vlakno(
    config.PROVIDER_CLAUDE,
    config.MODEL_CLAUDE_MID,
    config.REASONING_MID,
    PERMISSION_EDIT,
    config=config,
) as agent:
    print(agent.poloz_dotaz("Uprav validaci konfigurace podle README."))
```

### Více vláken současně

```python
from agent import AgentConfig, PERMISSION_EDIT, PERMISSION_REVIEW, vytvor_vlakno

config = AgentConfig.nacti()

with vytvor_vlakno(
    config.PROVIDER_CODEX,
    config.MODEL_CODEX_MID,
    config.REASONING_MID,
    PERMISSION_EDIT,
    config=config,
) as codex, vytvor_vlakno(
    config.PROVIDER_CLAUDE,
    config.MODEL_CLAUDE_LOW,
    config.REASONING_LOW,
    PERMISSION_REVIEW,
    config=config,
) as claude:
    print(codex.poloz_dotaz("Navrhni implementaci."))
    print(claude.poloz_dotaz("Zkontroluj návrh na rizika."))
```

Metody jsou dostupné i s diakritikou (`polož_dotaz`) jako alias k `poloz_dotaz`.

## Oprávnění

Každé vlákno se zakládá s jednotným profilem oprávnění:

| Profil | Konstanta | Účel |
| --- | --- | --- |
| `review` | `PERMISSION_REVIEW` | čtení, vyhledávání, analýza bez úprav |
| `edit` | `PERMISSION_EDIT` | úpravy souborů v bezpečnějším rozsahu |
| `full` | `PERMISSION_FULL` | plný režim, používat jen pro důvěryhodné úlohy |

Interní mapování:

| Profil | Codex | Claude |
| --- | --- | --- |
| `review` | `ApprovalMode.deny_all`, `Sandbox.read_only` | `Read`, `Grep`, `Glob` |
| `edit` | `ApprovalMode.deny_all`, `Sandbox.workspace_write` | `Read`, `Grep`, `Glob`, `Edit`, `Write` |
| `full` | `ApprovalMode.deny_all`, `Sandbox.full_access` | `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash` |

Claude vždy používá `permission_mode="dontAsk"`. Codex vždy používá `ApprovalMode.deny_all`. To znamená: žádná potvrzovací okna; co není povolené profilem, nebude ručně schvalováno.

## API

```python
vytvor_vlakno(
    provider: str,
    model: str,
    reasoning: str,
    permission_profile: str,
    *,
    config: AgentConfig | None = None,
) -> CodexVlakno | ClaudeVlakno
```

Parametry:

| Parametr | Popis |
| --- | --- |
| `provider` | `config.PROVIDER_CODEX` nebo `config.PROVIDER_CLAUDE` |
| `model` | jedna z hodnot `config.MODEL_CODEX_*` nebo `config.MODEL_CLAUDE_*` |
| `reasoning` | `config.REASONING_LOW`, `config.REASONING_MID`, `config.REASONING_HIGH` |
| `permission_profile` | `PERMISSION_REVIEW`, `PERMISSION_EDIT`, `PERMISSION_FULL` |
| `config` | načtený `AgentConfig`; pokud chybí, načte se automaticky |

Validace probíhá před založením vlákna:

- provider musí být známý,
- reasoning musí být podporovaný providerem,
- model musí patřit ke zvolenému provideru podle `.env`,
- permission profil musí být jeden z `review/edit/full`.

## Lifecycle

Vlákna vždy zavírejte:

```python
vlakno = vytvor_vlakno(...)
try:
    print(vlakno.poloz_dotaz("..."))
finally:
    vlakno.zavri()
```

Preferovaně používejte `with`, které zavření řeší automaticky.

Dotazy na stejné instanci jsou serializované interním lockem. Pro paralelní práci vytvořte více samostatných vláken.
