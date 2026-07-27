# Aktualizace: kontraktový workflow

Balíček přidává:

- `contract_workflow.py` — model, ukládání, předávání a review kontraktů,
- `agent_console.py` — dlouho běžící konzoli pro architecta a programátora,
- základní profil `programmer`,
- kontraktové příkazy architecta,
- inboxy agentů a ownera,
- řízené zápisy do paměti,
- testy workflow.

## Instalace

Překopírujte obsah složky `agentCodex` do kořene repozitáře.

Balíček záměrně nepřepisuje:

- `agents/architect/MEMORY.md`,
- `agents/architect/WORKING_STATE.md`,
- existující soubory v `memory/`.

## Kontrola

```powershell
python -m compileall contract_workflow.py agent_console.py
python -m pytest -v
python agent_console.py
```
