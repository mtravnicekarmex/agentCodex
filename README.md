# agentCodex

A thin layer over the Codex SDK and the Claude Agent SDK with a shared
synchronous interface.

The project has two API levels:

- `create_thread(...)` – the low-level technical thread,
- `create_agent("architect", ...)` – a profiled agent with a role, memory,
  and commands.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Login

```powershell
python -m agents.agent
```

## Profiled agent

```python
from agents.agent import AgentConfig
from agents.agent_profile import create_agent

config = AgentConfig.load()

with create_agent("architect", config=config) as architect:
    print(architect.ask("Review the design of the new layer."))
```

## Talking to the architect

The only entry point at the repository root is `chat_architect.py` — a
single window onto the architect. There is no multi-agent console; the
reviewer and programmer are created internally to run the pipeline, but
you never chat with them directly (see ADR-021).

Run:

```powershell
python chat_architect.py
```

On start, the architect is briefed on the real contract queue and its own
inbox and greets you with that context — e.g. asking what is on the agenda
today — instead of a blind, ungrounded greeting. From there, plain text
goes straight to the architect; the following commands are also available
alongside the conversation:

```text
/new <topic>       architect creates IMPLEMENTATION_CONTRACT_NNNN.md (DRAFT);
                  from there the pipeline runs automatically (architecture
                  review, and if ACCEPTED, implementation and implementation
                  review too) and stops once it returns to the architect
/revise <n> <topic> architect rewrites the contract's requirements after
                  CHANGES_REQUESTED from architecture review, resubmits it
                  for review, and continues automatically the same way
/work [n]         manual override: programmer picks up contract <n> (or the
                  next ready one) — not needed in the normal flow
/review [n]       manual override: architect runs implementation review on
                  contract <n> (or the next ready one) — not needed in the
                  normal flow
/commit <n>       after discussing the implementation review result with
                  the architect and agreeing it is sufficient, commits and
                  pushes contract <n> (must be APPROVED)
/status           shows the queue and handoffs
/inbox            shows the architect's inbox
/help             shows this list again
/exit             exits
```

### Lifecycle

Three roles, two review gates, after the Tr5 Platform Implementation
Contract pattern (Architect / Architecture Reviewer / Implementation
Agent): the contract is first assessed by an INDEPENDENT reviewer, before
the programmer ever sees it (Architecture Review); after implementation the
architect assesses the result (Implementation Review). The architect never
approves its own proposal.

Owner approval happens once, at `/new`/`/revise` — from there the pipeline
runs unattended (architecture review → programmer → implementation review)
and stops again only once it returns to the architect, whatever the
verdict (`APPROVED` or `CHANGES_REQUESTED`), the same way
`ARCHITECTURE_CHANGES_REQUESTED`/`REJECTED` already stop there today (see
ADR-018).

Two git checkpoints (see ADR-019): right after architecture review accepts
a contract, before the programmer touches anything, the working tree is
committed and pushed as `CONTRACT_NNNN` — the last clean state before
implementation starts. After implementation review, once the owner has
discussed the result with the architect and both agree it is sufficient,
`/commit <n>` commits and pushes as `CONTRACT_NNNN - IMPLEMENTED`. Neither
commit happens if there is nothing to commit.

```text
architect (create_contract)
  DRAFT → reviewer
                ↓  architecture review
  ACCEPTED → READY_FOR_PROGRAMMER          CHANGES_REQUESTED → ARCHITECTURE_CHANGES_REQUESTED → architect (/revise → back to reviewer)
      ↓                                      REJECTED → REJECTED (end, permanent record) → architect
programmer
  IN_PROGRESS
  READY_FOR_ARCHITECT_REVIEW
      ↓  implementation review (architect)
architect
  APPROVED → owner
  CHANGES_REQUESTED → programmer
```

Every contract contains (structure per the Tr5 Document Standard):

- Purpose and Intent — the architectural rationale, kept separate from the
  requirements,
- Current State, Inputs, Outputs, Out of Scope, Future Evolution,
- the requirements and acceptance criteria for every point (Functional
  Requirements),
- the programmer's note for every point, files touched, and tests,
- Architecture Review and Implementation Review as append-only rounds
  (`### Round N`) — review history is never overwritten,
- Completion Notes, Lessons Learned,
- current status and who it is handed off to.

Notifications are written to `agents/<agent>/INBOX.md`. Once approved, a
message is written to `contracts/OWNER_INBOX.md`.

During review the architect (implementation review) or reviewer
(architecture review) may propose controlled writes to:

```text
memory/*.md
agents/<agent>/MEMORY.md
agents/<agent>/WORKING_STATE.md
PRINCIPLES.md
```

The host code rejects any other target.

## Permissions

| Profile | Purpose |
| --- | --- |
| `review` | reading and analysis without changing code |
| `edit` | implementation work in the working project |
| `full` | full access including the shell; use sparingly |

The default workflow uses:

- architect: `review`,
- reviewer: `review`,
- programmer: `edit`.

## Roles

Mapping onto the Tr5 Platform Document Standard (Architect / Architecture
Reviewer / Implementation Agent):

| Agent | Tr5 role | Responsibility |
| --- | --- | --- |
| `architect` | Architect | Drafts contracts (Purpose/Intent/points); runs implementation review after implementation. |
| `reviewer` | Architecture Reviewer | Independently assesses the contract BEFORE implementation; the architect never approves its own proposal. |
| `programmer` | Implementation Agent | Implements exclusively what the contract specifies after architecture review `ACCEPTED`. |

## Tests

```powershell
python -m pytest -v
```
