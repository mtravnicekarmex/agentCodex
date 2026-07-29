# Update: contract workflow

Historical note (see `memory/DECISIONS.md`, ADR-021, ADR-029): the files
below (`contract_workflow.py`, `agent_console.py`) have since moved into
the `agents/` package (`agents/contract_workflow.py`, `agents/pipeline.py`);
`agent_console.py` itself was retired in favor of the single-window
`main.py` at the repository root (originally `chat_architect.py`, renamed
under ADR-029). This file itself also moved, from the repository root to
`agents/UPDATE_NOTES.md`, under the same ADR-029 reorganization. This note
is kept as a historical record of the original delivery, not as current
instructions — see `README.md` for how to actually run the project today.

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
