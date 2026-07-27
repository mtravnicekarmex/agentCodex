# Agent Suggestions

Jednotné profily oprávnění pro `vytvor_vlakno` i `vytvor_agenta`:

```python
PERMISSION_REVIEW = "review"
PERMISSION_EDIT = "edit"
PERMISSION_FULL = "full"
```

## Doporučené použití

- `review`: analýza a návrhy bez změn souborů,
- `edit`: bezpečnější implementační práce v workspace,
- `full`: pouze izolované nebo důvěryhodné úlohy.

Profilovaný agent vybírá oprávnění z `agents/<name>/config.json`.
