# Aktuální pracovní stav Architecta

## Aktivní téma

Zavedení vyšší vrstvy `vytvor_agenta()` nad stávající `vytvor_vlakno()`.

## Aktuální stav

- Profil agenta se načítá z `agents/<name>/config.json`.
- Role, soukromá paměť a pracovní stav se skládají do instrukcí vlákna.
- Příkazy se načítají ze souborů v `commands/`.
- Všichni agenti používají společný kořen projektu jako `cwd`.

## Další doporučené kroky

- Doplnit perzistenci Codex vláken.
- Vyjasnit ekvivalentní obnovení relace pro Claude.
- Přidat řízenou aktualizaci soukromé paměti.
- Přidat další profily agentů, například `programmer` a `reviewer`.
