# Agent Suggestions

Jednotne profily opravneni pro `vytvor_vlakno`:

```python
PERMISSION_REVIEW = "review"
PERMISSION_EDIT = "edit"
PERMISSION_FULL = "full"
```

## Mapovani opravneni

| Profil | Codex | Claude |
| --- | --- | --- |
| `review` | `ApprovalMode.deny_all`, `Sandbox.read_only` | `tools=["Read", "Grep", "Glob"]`, `allowed_tools` stejne, `permission_mode="dontAsk"` |
| `edit` | `ApprovalMode.deny_all`, `Sandbox.workspace_write` | `tools=["Read", "Grep", "Glob", "Edit", "Write"]`, `allowed_tools` stejne, `permission_mode="dontAsk"` |
| `full` | `ApprovalMode.deny_all`, `Sandbox.full_access` | `tools=["Read", "Grep", "Glob", "Edit", "Write", "Bash"]`, `allowed_tools` stejne, `permission_mode="dontAsk"` |

## Doporucene typy agentu

### Codex review agent

Pouziti pro revize kodu, analyzu a navrhy bez uprav souboru.

```python
config = AgentConfig.nacti()
agent = vytvor_vlakno(
    config.PROVIDER_CODEX,
    config.MODEL_CODEX_LOW,
    config.REASONING_LOW,
    PERMISSION_REVIEW,
    config=config,
)
```

### Codex edit agent

Pouziti pro implementacni praci v projektu s moznosti zapisovat do workspace.

```python
config = AgentConfig.nacti()
agent = vytvor_vlakno(
    config.PROVIDER_CODEX,
    config.MODEL_CODEX_MID,
    config.REASONING_MID,
    PERMISSION_EDIT,
    config=config,
)
```

### Claude review agent

Pouziti pro cteni, vyhledavani a analyzu bez uprav.

```python
config = AgentConfig.nacti()
agent = vytvor_vlakno(
    config.PROVIDER_CLAUDE,
    config.MODEL_CLAUDE_LOW,
    config.REASONING_LOW,
    PERMISSION_REVIEW,
    config=config,
)
```

### Claude edit agent

Pouziti pro upravy souboru bez spousteni shell prikazu.

```python
config = AgentConfig.nacti()
agent = vytvor_vlakno(
    config.PROVIDER_CLAUDE,
    config.MODEL_CLAUDE_MID,
    config.REASONING_MID,
    PERMISSION_EDIT,
    config=config,
)
```

### Full agent

Pouzivat jen pro izolovane nebo duveryhodne ulohy. U Codexu znamena `full_access`,
u Claude povoluje i `Bash`.

```python
config = AgentConfig.nacti()
agent = vytvor_vlakno(
    config.PROVIDER_CODEX,
    config.MODEL_CODEX_HIGH,
    config.REASONING_HIGH,
    PERMISSION_FULL,
    config=config,
)
```
