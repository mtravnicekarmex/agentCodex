# Dlouhodobá paměť agenta Architect

## Účel projektu

Projekt `agentCodex` poskytuje tenkou synchronní vrstvu nad OpenAI Codex SDK a Anthropic Claude Agent SDK. Oba provideři mají mít co nejvíce jednotné veřejné rozhraní pro dlouho žijící konverzační vlákno.

## Aktuální veřejné API

- `vytvor_vlakno(provider, model, reasoning, permission_profile, config=...)`
- `vytvor_agenta(agent_name, config=..., project_root=...)`
- `poloz_dotaz(text)` / `polož_dotaz(text)`
- `zavri()`
- context manager

## Důležité principy

- `vytvor_vlakno()` je nízkoúrovňová technická vrstva.
- `vytvor_agenta()` načítá roli, paměť, pracovní stav a příkazy.
- Všichni agenti pracují nad společným kořenem projektu.
- Konkrétní modely jsou v `.env`; agentní profil používá úrovně `low`, `mid`, `high`.
- Krátkodobá paměť je v aktivním vlákně.
- Dlouhodobá paměť je v Markdown souborech.
- Runtime data se nemají zaměňovat s verzovanou pamětí.

## Aktuální omezení

- Perzistence a obnovení vláken zatím nejsou implementovány.
- `persistent_thread` je připravená konfigurační volba pro další etapu.
- Architect používá výchozí profil `review`, takže nemění soubory.
