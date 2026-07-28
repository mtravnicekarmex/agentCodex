# Architect's Commands

- `create_contract` — drafts a new numbered contract (created in status
  DRAFT, goes straight to the `reviewer` agent for architecture review).
  Also used to revise a contract after `CHANGES_REQUESTED` (see
  `agent_console.py::revise_contract`).
- `review_contract` — implementation review AFTER implementation; checks
  every point against its acceptance criteria and proposes memory entries.
- `analyze_architecture` — runs an architectural analysis of a given part
  of the project (current state, strengths and weaknesses, technical
  debt, security risks, improvement proposals); does not edit files.
- `propose_change` — proposes an architectural change (goal, constraints,
  structure, files touched, API impact, compatibility, test scenarios,
  open decisions); does not edit files.
- `review_design` — runs an independent architectural review (API
  consistency, provider separation, thread lifecycle, memory,
  permissions, concurrency, error handling, compatibility, testability);
  does not edit files.
- `update_memory` — based on completed work, proposes an update to
  `agents/architect/MEMORY.md`; does not edit the file itself, only
  returns a proposal.

Reserved slots for future commands (no content yet): `delegate`, `plan`,
`summarize`.

Architecture review (assessing the contract BEFORE implementation) is run
by the `reviewer` agent, see `agents/reviewer/COMMANDS.md`.
