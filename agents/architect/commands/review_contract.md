Proveď architektonické review implementace tohoto kontraktu:

Soubor: {{CONTRACT_PATH}}

Obsah kontraktu:
<contract>
{{CONTRACT_CONTENT}}
</contract>

Přečti aktuální změněné zdrojové soubory a testy. Zkontroluj každý bod kontraktu.
Vrať pouze platný JSON:

{
  "approved": true,
  "summary": "celkové review",
  "reviews": [
    {
      "point": 1,
      "status": "APPROVED",
      "review": "konkrétní zjištění a ověření"
    }
  ],
  "memory_updates": [
    {
      "path": "memory/DECISIONS.md",
      "text": "trvalé a ověřené zjištění"
    },
    {
      "path": "agents/programmer/MEMORY.md",
      "text": "zjištění důležité pro další práci programátora"
    }
  ]
}

Pravidla:
- review musí existovat pro každý bod,
- status je pouze APPROVED nebo CHANGES_REQUESTED,
- approved smí být true jen tehdy, když jsou všechny body APPROVED,
- memory_updates mohou být prázdný seznam,
- do paměti neukládej celý kontrakt ani dočasné detaily.
