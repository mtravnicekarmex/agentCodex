# Contracts

Contracts are the single source of truth for handing off work between
agents. The structure and naming follow the Tr5 Platform Document Standard
(Implementation Contract Template).

File names (four-digit number, never reused, no hyphens):

```text
IMPLEMENTATION_CONTRACT_0001.md
IMPLEMENTATION_CONTRACT_0002.md
```

A contract always separates two layers:

- **Why** (Purpose, Intent) — the architectural rationale, belongs to humans.
- **What** (points / Functional Requirements, Acceptance Criteria) —
  precise, testable specification, belongs to implementation.

## Roles

- `architect` — drafts the contract (`create_contract`); runs
  implementation review after implementation.
- `reviewer` — independently runs architecture review BEFORE
  implementation; the architect never approves its own proposal.
- `programmer` — implements only contracts that have passed architecture
  review with verdict `ACCEPTED`.

## Statuses (two review gates)

1. `DRAFT` — contract created, handed off to `reviewer` for architecture
   review.
2. `ARCHITECTURE_CHANGES_REQUESTED` — the reviewer requires the
   requirements to be rewritten; handed back to `architect`
   (`revise_contract`); after revision it returns to `DRAFT` and is handed
   back to `reviewer` for re-assessment.
3. `REJECTED` — the request as a whole was rejected in architecture
   review; the contract does not proceed further, but stays in the
   repository as a permanent record.
4. `READY_FOR_PROGRAMMER` — architecture review ended with verdict
   `ACCEPTED`.
5. `IN_PROGRESS` — the programmer has claimed the contract.
6. `READY_FOR_ARCHITECT_REVIEW` — implementation is done, awaiting
   implementation review.
7. `CHANGES_REQUESTED` — implementation review requires a fix; returned to
   the programmer.
8. `APPROVED` — implementation review approved every point; handed off to
   the owner.

The `Handed off to` field determines the next participant in the workflow.
A notification is written at the same time to `agents/<agent>/INBOX.md`.
Approved contracts are handed off to the project owner and appear in
`contracts/OWNER_INBOX.md`.

Do not edit contracts by hand unless an emergency fix is needed. The
visible Markdown is generated from metadata stored at the end of each
file. The history of both review gates (`Architecture Review`,
`Implementation Review`) is append-only — each round is added as a new
`### Round N` section, older rounds are never overwritten or deleted. The
contract's requirements (points, Purpose, Intent, ...) may only be
rewritten via `revise_contract`, and only while the contract is in status
`ARCHITECTURE_CHANGES_REQUESTED` — once it has passed architecture review
with verdict `ACCEPTED`, the requirements no longer change; only
annotations and review do.
