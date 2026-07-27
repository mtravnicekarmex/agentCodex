# agentCodex

Tenká vrstva nad [Codex SDK](https://github.com/openai/codex) a [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Oba providery zpřístupňuje přes stejné synchronní rozhraní.

Projekt má dvě úrovně API:

- `vytvor_vlakno(...)` – nízkoúrovňové technické vlákno,
- `vytvor_agenta("architect", ...)` – profilovaný agent s rolí, pamětí a příkazy.

## Instalace

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Zkopírujte `.env.example` do `.env` a upravte modely podle účtů, které používáte.

## Přihlášení

```bash
python agent.py
```

Přihlášení je jediný povolený interaktivní krok.

## Nízkoúrovňové vlákno

Stávající API zůstává funkční:

```python
from agent import AgentConfig, PERMISSION_REVIEW, vytvor_vlakno

config = AgentConfig.nacti()

with vytvor_vlakno(
    config.PROVIDER_CODEX,
    config.MODEL_CODEX_LOW,
    config.REASONING_LOW,
    PERMISSION_REVIEW,
    config=config,
) as vlakno:
    print(vlakno.poloz_dotaz("Udělej revizi souboru agent.py."))
```

`vytvor_vlakno()` nově přijímá volitelný keyword argument `instructions`. Běžný kód jej nemusí používat; slouží vyšší agentní vrstvě.

## Profilovaný agent

```python
from agent import AgentConfig
from agent_profile import vytvor_agenta

config = AgentConfig.nacti()

with vytvor_agenta("architect", config=config) as architect:
    print(
        architect.poloz_dotaz(
            "Posuď současné rozdělení nízké a vysoké agentní vrstvy."
        )
    )
```

Předdefinovaný příkaz:

```python
with vytvor_agenta("architect", config=config) as architect:
    print(
        architect.spust_prikaz(
            "propose_change",
            task="Navrhni perzistenci vláken pro oba providery.",
        )
    )
```

## Struktura profilu agenta

```text
agents/<name>/
├── config.json
├── ROLE.md
├── MEMORY.md
├── WORKING_STATE.md
├── COMMANDS.md
├── commands/
└── runtime/
```

- `config.json` vybírá provider, modelový profil, reasoning a oprávnění.
- `ROLE.md` obsahuje stabilní instrukce role.
- `MEMORY.md` je soukromá dlouhodobá paměť.
- `WORKING_STATE.md` obsahuje aktuální rozpracovaný kontext.
- `commands/*.md` jsou opakovaně použitelné šablony příkazů.
- `runtime/` je rezervováno pro budoucí perzistenci vláken a není verzováno.

Všichni agenti pracují nad stejným kořenem projektu. Jejich podsložka je profil, nikoli omezený pracovní adresář.

## Modelové profily

Agent používá v `config.json` hodnoty `low`, `mid`, `high`. Konkrétní model se vybere z `.env` podle provideru:

```json
{
  "provider": "codex",
  "model_profile": "high",
  "reasoning_profile": "high"
}
```

Tím lze později změnit konkrétní model v `.env` bez úprav všech agentních profilů.

## Oprávnění

| Profil | Codex | Claude |
| --- | --- | --- |
| `review` | `ApprovalMode.deny_all`, `Sandbox.read_only` | `Read`, `Grep`, `Glob` |
| `edit` | `ApprovalMode.deny_all`, `Sandbox.workspace_write` | `Read`, `Grep`, `Glob`, `Edit`, `Write` |
| `full` | `ApprovalMode.deny_all`, `Sandbox.full_access` | navíc `Bash` |

## Paměť

- krátkodobá paměť: aktivní konverzační vlákno,
- soukromá dlouhodobá paměť: `agents/<name>/MEMORY.md`,
- společná dlouhodobá paměť: `memory/*.md`.

Perzistence a obnovení vláken jsou připravené jako další etapa; první verze při každém `vytvor_agenta()` založí nové technické vlákno.

## Testy

```bash
pytest
```


## Pracovní adresář agenta

`vytvor_vlakno()` přijímá volitelný parametr `cwd`. Při vynechání používá
kořen tohoto repozitáře. `vytvor_agenta()` vždy předává svůj `project_root`,
takže profil agenta i provider pracují nad stejným projektem.
