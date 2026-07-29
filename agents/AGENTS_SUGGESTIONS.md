# Agent Suggestions

Shared permission profiles for both `create_thread` and `create_agent`:

```python
PERMISSION_REVIEW = "review"
PERMISSION_EDIT = "edit"
PERMISSION_FULL = "full"
```

## Recommended usage

- `review`: analysis and proposals without changing files,
- `edit`: safer implementation work in the workspace,
- `full`: isolated or trusted tasks only.

A profiled agent picks its permissions from `agents/<name>/config.json`.
