# Architektonická rozhodnutí

## ADR-001: Oddělení vlákna a agenta

- `vytvor_vlakno()` zůstává nízkoúrovňovým, zpětně kompatibilním API.
- `vytvor_agenta()` je vyšší vrstva pro roli, paměť, příkazy a budoucí runtime perzistenci.
- Všichni agenti používají stejný kořen projektu jako pracovní adresář.

## ADR-002: Dvě úrovně paměti

- Krátkodobá paměť je historie aktivního vlákna.
- Dlouhodobá paměť je v Markdown souborech.
