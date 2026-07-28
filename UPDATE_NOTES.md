# Update: contract workflow

This package adds:

- `contract_workflow.py` — the contract model, storage, handoff, and review,
- `agent_console.py` — a long-running console for the architect and the
  programmer,
- a basic `programmer` profile,
- the architect's contract commands,
- agent and owner inboxes,
- controlled memory writes,
- workflow tests.

## Installation

Copy the contents of the `agentCodex` folder into the root of the repository.

The package deliberately does not overwrite:

- `agents/architect/MEMORY.md`,
- `agents/architect/WORKING_STATE.md`,
- existing files in `memory/`.

## Verification

```powershell
python -m compileall contract_workflow.py agent_console.py
python -m pytest -v
python agent_console.py
```
