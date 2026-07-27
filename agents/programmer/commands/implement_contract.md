Implementuj tento kontrakt:

Soubor: {{CONTRACT_PATH}}

Obsah:
<contract>
{{CONTRACT_CONTENT}}
</contract>

Proveď skutečné změny ve zdrojových souborech. Po dokončení vrať pouze platný JSON:

{
  "summary": "souhrn implementace",
  "notes": [
    {
      "point": 1,
      "note": "co bylo konkrétně provedeno",
      "files": ["agent.py"],
      "tests": ["python -m pytest -v — 8 passed"]
    }
  ],
  "tests": [
    "souhrnný test nebo kontrola"
  ]
}

Pravidla:
- notes musí obsahovat právě jednu položku pro každý bod kontraktu,
- čísla point musí odpovídat kontraktu,
- uváděj jen skutečně změněné soubory a skutečně spuštěné testy,
- pokud něco nelze dokončit, popiš blokaci pravdivě; nevydávej bod za hotový.
