# Společná pravidla projektu

- Komunikuj česky, pokud zadání neurčí jinak.
- Pracovní adresář je kořen projektu.
- Před změnou kódu si přečti související soubory a veřejné API.
- Zachovávej jednotné rozhraní pro Codex a Claude, pokud je to možné.
- Provider-specifické detaily skrývej uvnitř implementační vrstvy.
- Neukládej hesla, tokeny ani přístupové údaje do repozitáře.
- Interaktivní může být pouze přihlášení provideru; ostatní běh nemá vyžadovat potvrzení.
- Dlouhodobý stav projektu je v adresáři `memory/`.
- Soukromé profily, paměť a příkazy agentů jsou v `agents/<name>/`.
