# agentCodex

Tenká vrstva nad Codex SDK a Claude Agent SDK se společným synchronním rozhraním.

Projekt má dvě úrovně API:

- `vytvor_vlakno(...)` – nízkoúrovňové technické vlákno,
- `vytvor_agenta("architect", ...)` – profilovaný agent s rolí, pamětí a příkazy.

## Instalace

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Přihlášení

```powershell
python agent.py
```

## Profilovaný agent

```python
from agent import AgentConfig
from agent_profile import vytvor_agenta

config = AgentConfig.nacti()

with vytvor_agenta("architect", config=config) as architect:
    print(architect.poloz_dotaz("Posuď návrh nové vrstvy."))
```

## Interaktivní workflow architect → programmer → architect

Spusťte:

```powershell
python agent_console.py
```

Nejdůležitější příkazy:

```text
/new <téma>   architect vytvoří CONTRACT - NNNN.md
/work         programmer převezme a implementuje nejbližší kontrakt
/review       architect provede review každého bodu
/status       zobrazí frontu a předání
/inbox <agent>
```

### Životní cyklus

```text
architect
  READY_FOR_PROGRAMMER
      ↓
programmer
  IN_PROGRESS
  READY_FOR_ARCHITECT_REVIEW
      ↓
architect
  APPROVED → owner
  CHANGES_REQUESTED → programmer
```

Každý kontrakt obsahuje:

- zadání a akceptační kritéria každého bodu,
- poznámku programátora ke každému bodu,
- dotčené soubory a testy,
- review architekta ke každému bodu,
- souhrn obou agentů,
- aktuální stav a adresáta předání.

Oznámení se zapisují do `agents/<agent>/INBOX.md`. Po schválení je zpráva
zapsána do `contracts/OWNER_INBOX.md`.

Architect může v review navrhnout řízené zápisy do:

```text
memory/*.md
agents/<agent>/MEMORY.md
agents/<agent>/WORKING_STATE.md
```

Hostitelský kód jiné cíle odmítne.

## Oprávnění

| Profil | Účel |
| --- | --- |
| `review` | čtení a analýza bez změny kódu |
| `edit` | úpravy souborů v pracovním projektu |
| `full` | plný přístup včetně shellu; používat výjimečně |

Výchozí workflow používá:

- architect: `review`,
- programmer: `edit`.

## Testy

```powershell
python -m pytest -v
```
