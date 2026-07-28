# Shared project rules

- Communicate in Czech during conversation, unless the task says otherwise.
  This rule covers conversation only — written documentation (this file and
  all other `.md` files in the project) is in English.
- The working directory is the project root.
- Read related files and the public API before changing code (see
  `PRINCIPLES.md` P7).
- Keep a unified interface for Codex and Claude wherever possible.
- Keep provider-specific details hidden inside the implementation layer.
- Never store passwords, tokens, or credentials in the repository.
- Only provider login may be interactive; nothing else should require
  confirmation.
- The project's long-term state lives in the `memory/` directory.
- Agents' private profiles, memory, and commands live in `agents/<name>/`.
- The actual application code being built through this pipeline lives in
  `project/`, kept separate from this agentic framework/governance layer
  (`agents/agent.py`, `agents/agent_profile.py`, `agents/contract_workflow.py`,
  `agents/git_ops.py`, `agents/pipeline.py`, `agents/<name>/`, `memory/`,
  `contracts/`, `AGENTS.md`, `PRINCIPLES.md`, and the single root entry
  point `chat_architect.py` — see ADR-021). This repository itself is the
  reusable starting state ("point zero") copied for each new project — see
  ADR-015.
- The repository root has exactly one `.py` file, `chat_architect.py` —
  the only way to run the pipeline. Everything else the framework needs is
  a module under `agents/` (see ADR-021).

## Naming convention (see ADR-008)

- Directories and source/code files: `lowercase_with_underscores`
  (e.g. `chat_architect.py`, `agents/contract_workflow.py`, `agents/reviewer/`).
- Document `.md` files that carry a rule, role, state, or contract (not
  free-form text): `UPPERCASE_WITH_UNDERSCORES.md` (e.g. `ROLE.md`,
  `AGENTS.md`, `MEMORY.md`, `IMPLEMENTATION_CONTRACT_0001.md`). `README.md`
  naturally fits the pattern.
- No diacritics in any file name, directory name, or identifier (variable,
  function, class) — ASCII only. This rule applies only to names; prose in
  documents, comments, and commit messages may and should use Czech
  diacritics (see "Communicate in Czech" above).
- No hyphens in file or directory names — use `_` instead of `-`.
- Numbered contracts: four digits, zero-padded, never reused
  (`IMPLEMENTATION_CONTRACT_0001.md`, `0002.md`, ...).

## Contract workflow

- Significant implementation work must have a
  `contracts/IMPLEMENTATION_CONTRACT_NNNN.md` file. See "Light path for
  small fixes" below for what counts as "significant".
- The architect prepares the requirements and, after implementation, runs
  implementation review, point by point. Architecture review of the
  contract BEFORE implementation is run independently by the `reviewer` —
  the architect never approves its own proposal.
- The programmer implements only the points of a contract that has passed
  architecture review with verdict `ACCEPTED`.
- The contract's status and `handoff_to` determine who continues.
- The host application writes notifications to `agents/<agent>/INBOX.md`.
- Permanent findings from review are written only to allowed memory files.
- The history of both review gates is append-only — a new round is added,
  the old one is never overwritten or deleted.

## Light path for small fixes (see `PRINCIPLES.md` P14, ADR-006)

Not every change needs a contract. Process weight should match decision
weight — the full contract cycle protects structural, hard-to-reverse
decisions; enforcing it on a typo would only slow the workflow down, not
protect anything.

The following may be fixed directly without a contract (by anyone — human
or agent):

- typos and formatting,
- broken or dead links,
- clearly incorrect text in a comment, in documentation, or in a `README`,
- any other mechanical fix that does not change behavior, the public API,
  or the structure.

Condition: such a fix must not introduce a new abstraction, function, file,
or dependency, nor change the behavior or output of the code. As soon as it
does (even a little), it needs a contract — when in doubt, choose the
contract, not the light path.

Every fix made this way is logged as one line in `memory/CHANGE_LOG.md`
(what was fixed, where, by whom) — otherwise it stays invisible to the next
review, the same way an uncommitted change does above.

## Principles

The project's operating principles (adopted from the Tr5 Platform and
generalized, plus this project's own — see ADR-005 and ADR-011) live in
`PRINCIPLES.md`, not here. That file is loaded in full into every agent's
instructions.
