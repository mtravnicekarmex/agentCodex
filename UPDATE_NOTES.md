# Aktualizace pracovního adresáře agentů

Balíček nahrazuje tyto soubory:

- `agent.py`
- `agent_profile.py`
- `tests/test_agent_profile.py`
- `README.md`

Změny:

- `vytvor_vlakno()` podporuje volitelný parametr `cwd`,
- Codex i Claude používají předaný pracovní adresář,
- `vytvor_agenta()` předává `project_root` do technického vlákna,
- `permission_profile` se validuje už při načítání profilu,
- přidány testy pro předání `cwd` a neplatné oprávnění.

Po překopírování spusťte:

```powershell
python -m compileall agent.py agent_profile.py
python -m pytest -v
python example_architect.py
```
