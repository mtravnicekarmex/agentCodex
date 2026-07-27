# Kontrakty

Kontrakty jsou jediný zdroj pravdy pro předávání práce mezi agenty.

Názvy souborů:

```text
CONTRACT - 0001.md
CONTRACT - 0002.md
```

Stavy:

1. `READY_FOR_PROGRAMMER`
2. `IN_PROGRESS`
3. `READY_FOR_ARCHITECT_REVIEW`
4. `CHANGES_REQUESTED` nebo `APPROVED`

Pole `Předáno komu` určuje dalšího účastníka workflow. Oznámení se zároveň
zapisuje do `agents/<agent>/INBOX.md`. Schválené kontrakty jsou předány vlastníkovi
projektu a objeví se v `contracts/OWNER_INBOX.md`.

Kontrakty neupravujte ručně, pokud není potřeba nouzová oprava. Viditelný Markdown
je generován z metadat uložených na konci každého souboru.
