# Architect's Current Working State

## Active topic

Introducing the higher-level `create_agent()` layer over the existing
`create_thread()`.

## Current state

- The agent profile is loaded from `agents/<name>/config.json`.
- Role, private memory, and working state are composed into the thread's
  instructions.
- Commands are loaded from files in `commands/`.
- All agents use the shared project root as their `cwd`.
- `programmer` and `reviewer` agent profiles have been added; the
  contract workflow now has three roles (Architect / Architecture
  Reviewer / Implementation Agent).

## Next recommended steps

- Add persistence for Codex threads.
- Clarify an equivalent session resumption for Claude.
- Add controlled updates to private memory.
- Add a `coordinator` agent profile.
