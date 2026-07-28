# agentCodex Principles

Status: Living Document

## Purpose

This document collects the operating principles of the `agentCodex` project.
Principles are adopted from the Tr5 Platform's own `PRINCIPLES.md` where they
apply, generalized to this project's own architecture (see ADR-005), and
otherwise added as this project accumulates its own experience. Numbering is
local to this document and assigned in the order a principle is adopted here
— it does not necessarily match the source principle's number in Tr5.

A principle exists here because it was agreed as a real, applicable rule for
this project, not because it sounded generally right in the source material.

## Revision Process

Each principle carries a `Status` field:

- **Active** — currently guiding decisions, no revision needed.
- **Under Review** — a recent case raised doubt; being reconsidered.
- **Revised** — superseded by a newer formulation (link to replacement).
- **Deprecated** — no longer applies; kept for historical record.

Principles are never silently deleted or renumbered. A deprecated or revised
principle stays in this document with a reason, so a later reader understands
why something that once made sense no longer does.

### When a principle gets reconsidered

Not on a fixed schedule, and not by auditing every principle after every
contract — that would itself violate P14/P15. A principle is reconsidered
when a real contract (typically during implementation review, sometimes
architecture review) actually runs into a conflict with it or a case it
does not cover, the same way Tr5's own P19-P24 were each extracted from a
specific incident, not from a review calendar.

When that happens: the reviewing agent (architect, or reviewer for
architecture review) may propose an entry to `PRINCIPLES.md` via
`memory_updates` (allowed since `PRINCIPLES.md` is in
`ALLOWED_MEMORY_TARGETS` — see ADR-014), describing the conflict and which
principle it concerns. This is appended, not a direct edit to the
principle's own `Status` field — `append_memory()` only appends a
timestamped entry. Formalizing the actual status change (`Active` →
`Under Review` → `Revised`/back to `Active`) and rewriting the principle's
own text is done deliberately afterward, referencing that entry, the same
way this document's own principles were drafted in conversation rather than
auto-generated.

## How agents use this file

The full content of this file is loaded into every agent's instructions
(see `agent_profile.py::build_agent_instructions`), the same way `ROLE.md` is
— so it does not depend on whether a given provider's SDK loads `AGENTS.md`
automatically.

## Principles

### P1 — Architecture defines direction. Implementation reflects today's understanding.
Status: Active
Source: Tr5 P1 + P2 (merged)

A contract may anticipate future evolution (in its "Future Evolution"
section). An implementation never does. No point of a contract, and no line
of its implementation, includes a capability that today's request did not
actually ask for — even if it seems obviously useful later.

### P2 — Verify deferred imports too, not just module-level ones.
Status: Active
Source: Tr5 P19

Checking dependencies only via `import`/`from` at the top of a file can miss
a library imported inside a function — the module then imports cleanly and
only fails at the actual call, with a real request waiting on an answer.

### P3 — An uncommitted local fix is invisible to the next review.
Status: Active
Source: Tr5 P20

Review always starts from a clean clone/state of the repository — anything
fixed locally and not committed does not exist from its point of view, and
can be silently overwritten by another change without anyone noticing.
Commit and push every verified fix before moving on to the next step.

### P4 — Verification isolated from real external systems must be structurally tied to that isolation, not just instructed.
Status: Active
Source: Tr5 P21

"Don't use the real key/DB" describes intent, not a mechanism — safe
isolation requires an explicit injected fake dependency, or another path
where there is no reachable code path to real credentials at all, not
relying on a test simply "not connecting".

### P5 — A gitignore entry for a sensitive or temporary path is an acceptance criterion of the change that introduces it.
Status: Active
Source: Tr5 P24

As soon as a contract or commit introduces a new default path for
credentials, tokens, or test/temporary output, verifying `.gitignore`
coverage belongs to that same step — not a separate cleanup task noticed
later.

### P6 — A contract's "Current State" contains facts, never interpretations.
Status: Active
Source: Tr5 P4

"Current State" describes only what already exists today — names, paths,
interfaces, behavior — established by reading the actual code. It never
contains a proposal, a wish, or a justification for changing something;
that belongs in "Purpose"/"Intent" instead. (Tr5 P3, on an automated
Discovery Engine generating this kind of document, was considered and
deferred — not adopted, see ADR-012 — since agentCodex has no such engine
and none is currently planned.)

### P7 — Establishing the actual current state precedes reasoning about what should change.
Status: Active
Source: Tr5 P5

No decision about what should change is made from memory or assumption.
The actual state of the relevant code and the public API is established
first — by reading it — before any requirement, contract, or fix is
proposed. (Operationally this is `AGENTS.md`'s "Read related files and the
public API before changing code"; this entry is the underlying reason that
rule exists, not a duplicate of it.)

### P8 — Every implementation begins with an explicit architectural intent.
Status: Active
Source: Tr5 P6

No code is written without a preceding contract that states why it is
needed, not only what it is. This is why every
`IMPLEMENTATION_CONTRACT_NNNN.md` has mandatory "Purpose" and "Intent"
fields, kept separate from the requirements themselves — the template
enforces the shape, this principle is the reason the shape exists.

### P9 — One decision, one source of truth — don't split it into separate human- and machine-facing artifacts before that split is actually needed.
Status: Active
Source: Tr5 P7 (generalized)

A human-readable representation and a machine-readable one can only
diverge in meaning if they are separate artifacts. Where possible, generate
both from a single source of truth instead of maintaining two files that
must be kept in sync by hand. This is why `contract_workflow.py` embeds the
`CONTRACT-META` JSON block directly inside the same `.md` file, generated
by the same `render_contract()` function from the same `Contract`
dataclass, instead of a separate `.json` package — divergence is
structurally impossible when there is only one file. If a real need for a
genuinely separate machine-facing artifact ever appears, that is a new
decision to make then, not a default to assume now (see P1).

### P10 — A disagreement between contract and implementation is a defect to resolve, not a matter of preference.
Status: Active
Source: Tr5 P8

If the actual implementation does not match what a contract's point
requires, that mismatch is a defect — it gets fixed, it is never treated as
an equally valid alternative reading. This is the reason implementation
review exists and is taken seriously: the architect checks every point
against its acceptance criteria, and any mismatch routes back to the
programmer as `CHANGES_REQUESTED`, not settled by preference.

This matters more here than in a single-reviewer setup, because the
architect who runs implementation review is a different agent than the
reviewer who ran architecture review before implementation — the architect
was not the one who accepted the contract. The reviewer's findings and
verdict (the `# Architecture Review` rounds) are part of the same rendered
contract file the architect reads during implementation review, so they
are structurally available; the architect's review command explicitly
directs attention to them (see `agents/architect/commands/review_contract.md`)
so what was actually accepted — not just the original point text in
isolation — is what the implementation is checked against.

### P11 — Validate a new structural decision on the smallest real case before generalizing it.
Status: Active
Source: Tr5 P9

A new pattern, tool, agent role, or structural convention is proven on the
smallest possible real case before it is generalized across the project.
Adding the `reviewer` role (ADR-003) is an example already behind us: it
was introduced as one concrete addition to the existing two-role workflow,
not designed upfront as a generic N-role framework. The same standard
applies to future structural additions — e.g. a future `coordinator`
profile should be piloted on one real case first, not designed in the
abstract.

### P12 — A contract's identity is permanent and independent of its changing content.
Status: Active
Source: Tr5 P10 (narrowed)

A contract's number identifies the decision itself, not a particular draft
of it. The number is assigned once, is never reused, and never changes —
not even when `revise_contract()` rewrites the requirements after
`ARCHITECTURE_CHANGES_REQUESTED`, and not across any number of review
rounds. This is why revision replaces a contract's content in place under
the same number instead of creating a new one, and why review history is
appended rather than overwriting — the file's identity persists through
every change to what it says.

### P13 — The programmer implements; it does not architect. A real gap is reported, not decided.
Status: Active
Source: Tr5 P11

An agent implementing a contract does not introduce abstractions,
features, or simplifications beyond what the contract specifies. If a
point leaves a real gap that requires an architectural decision — not just
a missing detail reasonably inferred from the contract and the existing
code — the programmer does not decide it. It implements only what is
unambiguous, describes the gap precisely in that point's note, and calls
it out in the overall summary so the architect sees it during
implementation review, instead of silently improvising. This is also why
the `programmer` profile's permissions are `edit`, not `full`, and why its
`ROLE.md` forbids direct edits to long-term memory.

### P14 — Process weight must match decision weight.
Status: Active
Source: Tr5 P12

The full contract pipeline exists to protect structural, hard-to-reverse
decisions. Small, reversible changes take the light path instead (see
`AGENTS.md` "Light path for small fixes", ADR-006). A process that taxes
every step, including trivial ones, eventually gets abandoned — and an
abandoned process protects nothing. This is why the light path exists at
all, not a workaround to the contract system but the other half of it.

### P15 — Standards are extracted from a working system, not invented in advance.
Status: Active
Source: Tr5 P13

A convention earns its place in this document by proving itself inside
real, observed work first — the constitutional layer stays minimal until
reality actually demands more. This is the method this migration itself
followed: P3 was deferred rather than adopted because no real case for it
exists yet (ADR-012), P10 was narrowed to only the part that actually
applies, and nothing was added "just in case."

_Tr5 P18 ("not every entity is a platform Artifact") was reviewed and not
adopted — see ADR-013. This closes the initial review of Tr5 P1-P13 and
P18. Future principles are still added the same way: appended above once
agreed, following the Revision Process above._
