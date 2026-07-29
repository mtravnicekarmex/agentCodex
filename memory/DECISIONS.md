# Architectural Decisions

## ADR-001: Separation of thread and agent

- `vytvor_vlakno()` remains the low-level, backward-compatible API.
- `vytvor_agenta()` is a higher layer for role, memory, commands, and
  future runtime persistence.
- All agents use the same project root as their working directory.

## ADR-002: Two levels of memory

- Short-term memory is the active thread's history.
- Long-term memory lives in Markdown files.

## ADR-003: Contract logic merged with the Tr5 Platform Document Standard

Decided while migrating values from the Tr5-platform project
(`github.com/trava5/Tr5-platform`).

- Contract files are named `IMPLEMENTATION_CONTRACT_NNNN.md` (no hyphens,
  four-digit number, never reused) instead of the previous
  `CONTRACT - NNNN.md`.
- The visible contract structure matches the Tr5 Implementation Contract
  Template (Title/Purpose/Intent/Current State/Inputs/Outputs/Functional
  Requirements/Out of Scope/Acceptance Criteria/Architecture
  Review/Future Evolution/Completion Notes/Implementation
  Review/Lessons Learned) — with no change to the automation underneath:
  `contract_workflow.py` still drives status programmatically via the
  `CONTRACT-META` JSON, it just renders it into Tr5's vocabulary.
- Added a second review gate: Architecture Review (the contract is
  assessed before implementation, new status `DRAFT` →
  `ARCHITECTURE_CHANGES_REQUESTED` / `REJECTED` / `READY_FOR_PROGRAMMER`)
  alongside the existing Implementation Review (after implementation, no
  change in logic, just renamed `record_architect_review` →
  `record_implementation_review`).
- The history of both review gates is append-only
  (`architecture_review_rounds`, `implementation_review_rounds`) — older
  review rounds are never overwritten, only new ones are added. The
  contract's requirements (points, Purpose, Intent, ...) may only be
  rewritten via `revise_contract`, and only while the contract has not yet
  passed architecture review with verdict `ACCEPTED`.
- Kept the per-point granularity (assignment + acceptance criteria +
  programmer note + architect review + status at the level of each
  individual point) — Tr5 reviews the contract as a whole, but per-point
  tracking is more precise and agentCodex already had it working, so it
  remains as a deliberate extension beyond the Tr5 template.

## ADR-004: Third agent `reviewer` — independent architecture review

Decided while migrating values from the Tr5-platform project, as a
follow-up to ADR-003.

- Tr5 distinguishes three roles: Architect / Implementation Agent /
  Architecture Reviewer. After ADR-003, agentCodex only had two
  (`architect` ran architecture review on its own proposal). Added a
  separate `agents/reviewer/` profile (`config.json`, `ROLE.md`,
  `MEMORY.md`, `WORKING_STATE.md`, `COMMANDS.md`,
  `commands/architecture_review.md`, `permission_profile: review`) — the
  architect no longer approves its own contract.
- `Contract.reviewer` (default `"reviewer"`) determines who the contract is
  handed off to after creation/revision. `create_contract`/`revise_contract`
  set `handoff_to` to the reviewer instead of the architect.
  `record_architecture_review` is now reserved for status `DRAFT` (the
  earlier re-review from `ARCHITECTURE_CHANGES_REQUESTED` now goes through
  `revise_contract`, which returns the contract to `DRAFT` and hands it
  back to the reviewer).
- Added the `next_for_revision()` method — the architect's queue of
  contracts returned by the reviewer for rewriting, separate from
  `next_for_architecture_review()` (the reviewer's queue of new/revised
  drafts).
- Implementation review (after implementation) stays with `architect` —
  Tr5 itself does not unambiguously name a role for this step (the roles
  table in Tr5's `PRINCIPLES.md` and `DOCUMENT_STANDARD.md` §3.2 do not
  agree on this point), and in Tr5-platform's actual practice (see
  `CLAUDE.md`) the same party (Claude) plays both the Architect and the
  Reviewer role, so full separation would go beyond what Tr5 itself
  practices.

## ADR-005: Four general principles adopted from Tr5 PRINCIPLES.md into AGENTS.md

Decided while migrating values from the Tr5-platform project.

- Tr5's `PRINCIPLES.md` contains principles P14–P24, derived from specific
  incidents. Most of them (P14, P15, P16, P17, P22, P23) are tied to
  specific technologies and tools that agentCodex does not use and does
  not have (Discovery Engine, pyaudio, Google Calendar API, Gemini,
  `platform_shell`) — these are not adopted.
- Only four principles were adopted, rewritten into a general,
  technology-neutral form with no mention of the original incident or
  technology, as a new "Principles" section in `AGENTS.md`:
  - P19 → verify deferred imports too, not just module-level ones.
  - P20 → an uncommitted local fix is invisible to the next review.
  - P21 → isolation from real external systems must be structural, not
    just instructed.
  - P24 → a gitignore entry for a sensitive/temporary path is an
    acceptance criterion of the change that introduces it, not a
    follow-up cleanup.
- Decided not to create a separate, immutable "worldview" document (like
  Tr5's `FOUNDATIONAL_WORLDVIEW.md`) — agentCodex is a smaller, practical
  project; values are folded directly into `AGENTS.md` (rules) and
  `DECISIONS.md` (rationale and origin), with no extra documentation layer.
- P20 already has a real precedent in agentCodex: while working on
  ADR-003/ADR-004, uncommitted local changes were found in the repository
  (`chat_architect.py`, `agents/architect/runtime/thread.json`, `.idea/*`)
  predating this migration — exactly the scenario P20 describes.

## ADR-006: Light path for small fixes without a contract (P12)

Decided while migrating values from the Tr5-platform project. Purpose
adopted unchanged from Tr5: allow quick fixes such as a typo or a broken
link on the fly, without disrupting the contract workflow, while clearly
separating a mechanical fix from a case where the architecture needs to be
stopped and rethought.

- New "Light path for small fixes" section in `AGENTS.md`: mechanical
  fixes (typos, dead links, formatting, clearly incorrect text in
  documentation/comments) do not need a contract, as long as they do not
  introduce a new abstraction/file/dependency and do not change behavior
  or the public API. When in doubt, choose the contract.
- Every such fix is logged as one line in `memory/CHANGE_LOG.md` — a file
  that was unused and empty until now (see the agentCodex review, item
  1-4) now has a concrete purpose.
- `agents/programmer/ROLE.md` got an explicit exception to the "do not
  edit long-term memory directly" rule for `memory/CHANGE_LOG.md` —
  otherwise the new `AGENTS.md` section and the existing role boundary
  would directly conflict. Other memory files (`DECISIONS.md`,
  `PROJECT_STATE.md`, `OPEN_TASKS.md`, `agents/<agent>/MEMORY.md`) are not
  affected by this exception — those are still only written to through
  architect-approved `memory_updates` during implementation review.
- No code-level enforcement layer (unlike `ContractStore`) — the light
  path is, by nature, outside the contract state machine; direct file
  edits have no such mechanism, just as in Tr5.

## ADR-007: Tr5's directory structure (`artifacts/foundation`, `tools/`, `projects/`) is not adopted

Decided while migrating values from the Tr5-platform project. agentCodex
has its own, already established and working structure (`agents/<name>/`,
`contracts/`, `memory/`, code at the project root) and it is kept
unchanged. Values and rules are adopted (contract logic, roles, principles
— ADR-003 through ADR-006), not the physical layout of directories. This
is consistent with ADR-005 (no separate `artifacts/foundation` layer for a
worldview) — agentCodex does not adopt Tr5's "platform vs. tools vs.
projects" layering, because it does not itself host nested projects.

## ADR-008: Formalizing the naming convention from the Tr5 Document Standard

Decided while migrating values from the Tr5-platform project. agentCodex
already followed the convention in practice (`UPPERCASE.md` for
ROLE/MEMORY/COMMANDS/WORKING_STATE/AGENTS/README,
`lowercase_with_underscores` for directories and code), it just was never
written down as a rule — it was a coincidence, not a deliberate choice.

- New "Naming convention" section in `AGENTS.md`:
  `lowercase_with_underscores` for directories/code,
  `UPPERCASE_WITH_UNDERSCORES.md` for rule-bearing documents, no
  diacritics or hyphens in names (prose, comments, and commit messages
  keep diacritics), a four-digit, never-reused contract number.
- Verified with a repository scan that no existing file/directory in the
  project (other than `.venv`/`__pycache__`, which are not subject to the
  convention) violates the rule — this is not a retroactive cleanup, just
  writing down what already held true.
- The rule was also added to `agents/architect/ROLE.md` (a new
  file/directory proposed in a contract), `agents/programmer/ROLE.md`
  (what the programmer itself names), and to the checklist in
  `agents/reviewer/commands/architecture_review.md` — so it holds even
  when `AGENTS.md` itself may not be part of a given provider's context
  (Codex/Claude SDK), while `ROLE.md` always is
  (`agent_profile.py::build_agent_instructions`).

## ADR-009: Project documentation and generated text translated to English

Decided after a discussion outside this project, applied here as well:
all `.md` files, and any Python code that generates `.md`-like or
agent/user-facing text, are written in English — matching the language
Tr5-platform's own `.md` files are written in.

- Scope: every `.md` file in the repository (governance docs, `ROLE.md`/
  `MEMORY.md`/`WORKING_STATE.md`/`COMMANDS.md`/`INBOX.md` for every agent,
  command prompts, `README.md` files, `memory/*.md`, this file), plus the
  Python-generated text that used to be Czech: `contract_workflow.py`
  (`render_contract` section labels, exception messages, docstrings,
  `notify()` event text), `agent.py`, `agent_profile.py`, and
  `agent_console.py` (help text, status/error messages, docstrings). Test
  files were updated to match the new English strings and messages.
- Explicitly out of scope: Python identifiers (function, variable, class,
  and attribute names, e.g. `vytvor_agenta`, `poloz_dotaz`, `vytvor_vlakno`,
  `zavri`, `nazev`). Renaming those is a public-API/code-style decision,
  not a documentation-language decision, and was not part of what was
  asked; changing them would be a much larger, higher-risk, unrelated
  change.
- Conversational language is unchanged: `AGENTS.md`'s "Communicate in
  Czech" rule stays in force for actual conversation with an agent (or
  with Claude in this migration) — only the written artifacts changed
  language, not how people and agents talk to each other.
- `PRINCIPLES.md` (see the "Principles" discussion, P1–P13 and P18) is
  created directly in English once that work resumes; it did not need
  translating since it did not exist yet at the time of this decision.

## ADR-010: Python identifiers translated to English

Supersedes the "explicitly out of scope" note in ADR-009: Czech is reserved
strictly for live conversation with agents/Claude; nothing else — including
internal code identifiers — stays Czech.

- Renamed across `agent.py`, `agent_profile.py`, `agent_console.py`,
  `chat_architect.py`, `example_architect.py`, and both test files:
  `vytvor_vlakno`→`create_thread`, `vytvor_agenta`→`create_agent`,
  `poloz_dotaz`→`ask`, `spust_prikaz`→`run_command`, `zavri`→`close`,
  `nazev`→`name`, `AgentVlakno`→`AgentThread`, `CodexVlakno`→`CodexThread`,
  `ClaudeVlakno`→`ClaudeThread`, `AgentConfig.nacti`→`.load`,
  `.over`→`.validate`, `.modely_pro`→`.models_for`, and the internal
  `_over_*`/`_codex_opravneni`/`_claude_opravneni`/`prihlaseni*`/
  `inicializuj_prihlaseni`/`_zavreno`/`_spustit_loop`/`loop_bezi`/`_spusti`/
  `_poloz_dotaz_async` helpers and locals.
- Updated references in `README.md`, `agents/architect/MEMORY.md`,
  `agents/architect/WORKING_STATE.md`, `memory/PROJECT_STATE.md`, and
  `AGENTS_SUGGESTIONS.md` to the new names.
- ADR-001 and ADR-009 are left as-is (append-only); their text reflects the
  names that were current at the time each was written.
- Verified with `py_compile` on all `.py` files and a full pytest run.

## ADR-011: Standalone PRINCIPLES.md, always loaded in full

Created `PRINCIPLES.md` as the single home for the project's operating
principles (see the "Principles" discussion, A7). Resolves both the "where
do principles live" question and the AGENTS.md-may-not-load-automatically
risk already known from ROLE.md (see ADR context around the naming
convention).

- `PRINCIPLES.md` follows the Tr5 format: Purpose, Revision Process (Status:
  Active / Under Review / Revised / Deprecated, append-only, never
  renumbered), then numbered principles. Numbering is local to this
  document (assigned in adoption order), with a `Source: Tr5 P#` note for
  traceability where a principle comes from Tr5.
- The 4 principles already adopted in C4 (Tr5 P19/P20/P21/P24, previously
  living directly in `AGENTS.md`) were moved into `PRINCIPLES.md` as P2-P5,
  so there is one canonical list instead of two. `AGENTS.md`'s "Principles"
  section is now a one-line pointer.
- P1 in `PRINCIPLES.md` is the already-agreed merge of Tr5 P1 + P2
  ("architecture defines direction, implementation reflects today's
  understanding").
- Delivery mechanism: `agent_profile.py::build_agent_instructions()` now
  always loads the full content of `PRINCIPLES.md` into every agent's
  instructions (new `AgentProfile.load_principles()`, new
  `AgentProfileConfig.load_principles` flag, default `True`), the same
  guaranteed way `ROLE.md` is loaded — chosen over a pointer-only reference
  or a short always-loaded summary, to make sure principles reach the model
  regardless of provider-side `AGENTS.md` auto-loading behavior.
- Remaining Tr5 candidates (P3-P13, P18) are being reviewed one at a time
  and appended to `PRINCIPLES.md` as each is agreed.

## ADR-012: Tr5 P3 ("Discovery observes reality") deferred, not adopted

Tr5 P3 states that a tool whose purpose is to describe current system state
(the Discovery Engine, generating `TR5_CURRENT_STATE.md`) must only report
what exists, never prescribe structure. agentCodex has no Discovery Engine
and none is planned.

- The underlying need P3 protects against — drift between assumed and
  actual repo state — is already covered here by a different mechanism:
  git history itself, `memory/CHANGE_LOG.md` (light-path fixes),
  `memory/PROJECT_STATE.md`, `memory/DECISIONS.md`, and each contract's own
  manually-written "Current State" section.
- Building an automated Discovery Engine now, without a concrete case of
  drift actually occurring, would itself violate P1 (implement today's
  understanding, not tomorrow's assumption) and P13 (standards are
  extracted from a working system, not invented in advance) — both already
  adopted.
- Decision: not added to `PRINCIPLES.md`. Deferred, not rejected — revisit
  if agentCodex's scale or number of concurrent contributors ever produces
  a real, observed mismatch between assumed and actual repo state.

## ADR-013: Tr5 P18 ("not every entity is a platform Artifact") not adopted

Tr5 P18 distinguishes a "platform Artifact" (something with its own
identity, lifecycle, and review history at the platform level — a
Contract, a foundational document, a project) from an implementation
detail inside one (e.g. a single action function), so that not every
internal detail gets full-ceremony tracking.

- The term "Artifact" comes from Tr5's `FOUNDATIONAL_WORLDVIEW.md` ontology,
  which this project already declined to adopt as a separate document (C5).
- The underlying concern — don't apply contract-level ceremony to
  something smaller than a meaningful unit of work — is already covered in
  spirit by P14 (process weight matches decision weight) and by how a
  contract's points are scoped (a point covers a feature, not each
  individual file or function inside it).
- Unlike P9/P11 (P11/P13 in this document), there is no observed agentCodex
  case where over-granular contract tracking was actually attempted or
  caused a real problem.
- Decision: not added to `PRINCIPLES.md`, per P15 (standards are extracted
  from a working system, not invented in advance) — no demonstrated need
  yet. This closes the initial A7 review of Tr5 P1-P13 and P18; P1-P13
  produced this project's own P1-P15 (see ADR-011, ADR-012 above).

## ADR-014: Principle revision process, and PRINCIPLES.md as an allowed memory target

Resolves A8 (how principles get revised, tied to the `Status` field
already defined in `PRINCIPLES.md`'s Revision Process). Not on a fixed
schedule or a full audit after every contract — that would itself violate
P14/P15 — but triggered when a real contract (typically during
implementation review, sometimes architecture review) actually runs into
a conflict with a principle, the same way Tr5's own P19-P24 were each
extracted from a specific incident.

- `contract_workflow.py`'s `ALLOWED_MEMORY_TARGETS` now includes
  `PRINCIPLES.md` (previously only `memory/*.md` and
  `agents/*/(MEMORY|WORKING_STATE).md`), so the architect (or reviewer) can
  propose a review entry via `memory_updates` during review, the same
  mechanism already used for other memory files. This is a change to a
  write-permission boundary, not a light-path fix, so it is recorded here
  rather than in `memory/CHANGE_LOG.md`.
- `append_memory()` only appends a timestamped entry — it does not edit a
  specific principle's `Status` field in place. A proposed entry describes
  the conflict and which principle it concerns; formalizing the actual
  status change and rewriting the principle's text is done deliberately
  afterward, referencing that entry — mirroring how this document's own
  principles were drafted through discussion rather than generated
  automatically.
- Documented directly in `PRINCIPLES.md`'s "Revision Process" section
  ("When a principle gets reconsidered"), `README.md`'s list of allowed
  memory-update targets, and a new test
  (`test_allows_principles_memory_target`).
- Verified with `py_compile` and a full pytest run (14/14 passing).

## ADR-015: Tr5's README standard adopted for future sub-units, not the root README

Resolves A9. Tr5's `DOCUMENT_STANDARD.md` defines a minimal, rarely-changing
README shape for every significant Artifact/tool: `# <Name>` /
`## Purpose` / `## Current capabilities (vX.Y)` / `## Current limitations`
/ `## Planned evolution`.

- Adopted for future README files describing a self-contained unit inside
  this repository (e.g. `project/README.md`, and any future
  `agents/<name>/README.md` if one is ever added) — see `project/README.md`
  for the first real use.
- Not applied to the root `README.md`: Tr5's standard targets one Artifact
  among many inside a multi-project platform, describing responsibility
  rather than usage. agentCodex's root README currently serves a different,
  still-needed role for a single project — installation, login, usage
  examples, permissions, roles — that a minimal status summary would not
  replace. Revisit only if the root README's role actually changes.

## ADR-016: `project/` directory added; this repository is the reusable starting state for new projects

Following up on the wider direction discussed after A9: this repository is
copied as the starting state ("point zero" — governance, principles,
agentic framework already set up) for each new project; each copy then
lives its own life (its own `.md` files, its own memory), independent of
other copies.

- Added `project/` at the repository root, per `project/README.md` (using
  the ADR-015 README standard): holds the actual application code being
  built through the contract pipeline, kept separate from the
  framework/governance layer (`agent.py`, `agent_profile.py`,
  `contract_workflow.py`, `agents/`, `memory/`, `contracts/`, `AGENTS.md`,
  `PRINCIPLES.md`). Referenced from `AGENTS.md`.
- Confirmed unchanged: the review order built in C1/C3 (architect drafts →
  reviewer's architecture review BEFORE implementation → programmer →
  architect's implementation review AFTER, architect never approves its
  own proposal). A description of the pipeline in conversation used a
  shorthand order (contract → programmer → reviewer → architect); this did
  not mean to reopen C3.
- Confirmed human-approval point: the owner approves before the architect
  hands a contract off to the reviewer; after that, the existing gates
  (architecture review, implementation) proceed via the existing
  `agent_console.py` commands. Automatically chaining those steps into one
  unattended run (a "run" mode that only stops again once the pipeline
  returns to the architect) was discussed and explicitly deferred, not
  built now — directory structure and other foundations come first.
- Agent memory scope confirmed as already-intended: an agent's own
  conversational memory only needs to last for the current task/session;
  once a contract is hand off, the contract file itself is sufficient
  context for the next agent. This matches the existing default
  (`persistent_thread: false`) rather than requiring a new mechanism.
- Still open, not decided here: what the architect's own longer-lived
  memory should look like across sessions/contracts (distinct from the
  per-task point above).

## ADR-017: Architecture review can also propose memory_updates

Resolves the "architect's long-term memory" open item from ADR-016. An
agent (architect or reviewer) does not need to retain the conversation
behind a contract — the contract itself is the durable record of that
decision. What still needs a home is a fact that surfaces during review
and is worth keeping *beyond* that one contract (a recurring risk, a
principle worth revisiting, project-wide state) — the existing
`memory_updates` mechanism (`ALLOWED_MEMORY_TARGETS`: `memory/*.md`,
`agents/<agent>/(MEMORY|WORKING_STATE).md`, `PRINCIPLES.md`, see ADR-014)
already exists for exactly this, but was previously only reachable from
implementation review (`record_implementation_review`).

- `record_architecture_review()` now accepts an optional `memory_updates`
  parameter, applied via the existing `append_memory()` the same way
  implementation review already does. This was a gap, not a new
  mechanism — architecture review is precisely the point where a reviewer
  is likely to notice something worth remembering, before implementation
  even starts (the same way Tr5's own P19-P24 were each extracted from a
  specific review finding).
- `agents/reviewer/commands/architecture_review.md` now documents the
  optional `memory_updates` field, with the same guidance already given
  elsewhere: don't store the discussion, only a fact worth keeping.
- `agent_console.py::run_architecture_review()` forwards
  `memory_updates` from the reviewer's response, mirroring
  `review_next()`.
- `agents/architect/MEMORY.md` (and any agent's private `MEMORY.md`) is
  not retired and not scope-restricted — it stays one of the allowed
  targets, written to only when a review actually surfaces something
  worth keeping, not maintained as a standing reference document. This
  also explains why it went stale before: nothing wrote to it in the
  normal flow of work.
- New test: `test_architecture_review_accepts_memory_updates`. Verified
  with `py_compile` and a full pytest run (15/15 passing).

## ADR-018: `/new` and `/revise` auto-chain the pipeline through to the architect

Previously `agent_console.py` required three manual commands per contract
(`/new`, then `/work`, then `/review`) even on the happy path. Per the
owner's description of the intended workflow: approval happens once, when
the owner is satisfied enough with the discussed intent to issue `/new` (or
`/revise`) — from there the pipeline should run unattended and stop again
only once it returns to the architect, where the owner and architect
discuss the outcome together.

- `create_contract()` and `revise_contract()` now call the reviewer's
  architecture review as before, then, only if the verdict produced
  `READY_FOR_PROGRAMMER`, automatically continue through the programmer's
  implementation and the architect's implementation review via a new
  `continue_pipeline()` helper. `CHANGES_REQUESTED`/`REJECTED` from
  architecture review already stop at the architect/owner today — nothing
  to chain, no change there.
- The chain always stops once implementation review returns — whether
  `APPROVED` or `CHANGES_REQUESTED` — rather than automatically retrying
  the programmer. Every return to the architect is a checkpoint for the
  owner, not a loop the system should keep running unattended; a second
  attempt (if requested) goes back through `/work`/`/review` deliberately,
  same as before.
- `implement_next()` and `review_next()` now accept an optional `number`
  parameter (chained calls target the specific contract just handed off,
  instead of picking "whatever is next in the queue," which could have
  grabbed an unrelated contract if more than one was in flight). Bare
  `/work` and `/review` (no argument) keep the old queue-picking behavior
  as a manual override; `/work <n>` and `/review <n>` now also work
  directly on a specific contract.
- If any step in the chain fails (e.g. invalid JSON from a model), it
  raises the same way `/work`/`/review` already did — nothing partially
  written, the contract stays in its last valid state, the owner resumes
  manually via `/work`/`/review` once the cause is clear. No new
  error-handling behavior was introduced.
- Explicitly out of scope for now (per the owner): letting `agent_console.py`
  itself launch the very first `/new` unattended, or any change to where
  the owner-approval point sits. Only the already-approved middle of the
  pipeline was automated.
- New tests in `tests/test_agent_console.py`
  (`test_create_contract_chains_through_to_implementation_review`,
  `test_create_contract_stops_when_changes_requested_at_architecture_review`,
  `test_create_contract_stops_after_changes_requested_implementation_review`),
  using a scripted fake agent (`.run_command()` only) instead of a real
  provider thread. Verified with `py_compile` and a full pytest run
  (18/18 passing).

## ADR-019: Git checkpoints wired into the pipeline (before implementation, after approval)

Per the owner's direction: the pipeline now commits and pushes at two
points, giving every contract a git-level "before" and "after" of the
programmer's work — a concrete implementation of `PRINCIPLES.md` P3
("an uncommitted local fix is invisible to the next review").

- New `git_ops.py` (`commit_and_push(project_root, message)`): stages
  everything (`git add -A`), checks via `git diff --cached --quiet`
  whether there is anything to commit (returns `False`, not an error, if
  the tree is already clean), commits, and pushes. Any git failure
  (including a failed push) raises `RuntimeError` — the caller does not
  proceed on top of an unsaved state, same policy as the rest of the
  pipeline (nothing partially done, no silent retry).
- `continue_pipeline()` (`agent_console.py`) now commits as
  `CONTRACT_NNNN` right after architecture review produces
  `READY_FOR_PROGRAMMER`, before calling the programmer — the last clean
  checkpoint before implementation starts.
- New `/commit <n>` console command runs `commit_approved_contract()`,
  which requires the contract's status to be `APPROVED` (refuses
  otherwise) and commits as `CONTRACT_NNNN - IMPLEMENTED`. This is
  deliberately a separate, explicit, owner-issued command rather than
  something `review_next()` triggers automatically on `APPROVED` — the
  owner explicitly wants to discuss the implementation review result with
  the architect first and only commit once they agree it is sufficient,
  not fold that judgment into an automatic status check.
- Message format follows the owner's own wording literally
  (`CONTRACT_NNNN`, not `IMPLEMENTATION_CONTRACT_NNNN` as used elsewhere)
  — a deliberate, narrower, git-log-specific label, not a naming
  convention change (`AGENTS.md`'s naming convention still governs file
  and identifier names, not commit message text).
- New `tests/test_git_ops.py`, exercising `commit_and_push()` against a
  real local git repository and a real (local, bare) remote — commit and
  push both verified to actually happen, not mocked. New tests in
  `tests/test_agent_console.py` verify `continue_pipeline()` and
  `commit_approved_contract()` call `commit_and_push()` with the right
  message at the right point, using a fake in place of `git_ops` (no real
  repository needed for the console-level tests). Verified with
  `py_compile` and a full pytest run (23/23 passing).

## ADR-020: `bod-nula` is a periodic snapshot; `agentCodex` stays the dev repo

Checked whether `github.com/mtravnicekarmex/bod-nula.git` (a separate
repository the owner pushed a copy of this project's content to, under a
new name) was a faithful, clonable "point zero" for future projects. It
was — content was file-for-file identical to `agentCodex` (only the
README title was intentionally changed) and 23/23 tests passed from a
fresh clone. Found and fixed the same pre-existing hygiene gap in both
repositories: `.pytest-tmp/` (25 leftover test-fixture files, `bod-nula`
only) and `.idea/` (7 files, both repos, including two conflicting
`.iml` files in `bod-nula` — direct evidence of drift from copying without
cleanup) were tracked in git despite `.gitignore` never covering them
(this is revision point 1-2 from the very first review, previously
deferred). Fixed in both: `.gitignore` now excludes both paths, and the
already-tracked files were untracked via `git rm -r --cached` (owner
connected the `bod nula` local folder for direct access, same as
`agentCodex`, rather than being handed manual commands).

- Decided relationship going forward: `agentCodex` remains the framework's
  own development repository — this is where governance, principles, and
  the agentic pipeline itself keep evolving. `bod-nula` is a periodic,
  manually-refreshed snapshot of `agentCodex`, meant to be cloned as the
  clean starting point for an actual new project; once cloned for a real
  project it lives its own independent life (own `.md` files, own memory,
  no further syncing back). `bod-nula`'s own `README.md` now states this
  explicitly, pointing back to this ADR.
- Practical note for future snapshots: refresh `bod-nula` from a clean
  `agentCodex` state (tests passing, no local IDE/test-run cruft) rather
  than an arbitrary local checkout, so this specific problem does not
  recur on the next refresh.
- A stale `.git/index.lock` was left behind by `git rm --cached` in both
  local folders (the same mounted-filesystem permission quirk seen before
  with `rm`/`mv`) — harmless to read-only git commands, but needs manual
  deletion before the owner's next local `git add`/`commit` in either
  folder.
- Confirmed explicitly: this connected `bod nula` folder/repo stays a
  clean template forever. The first project (and every subsequent one) is
  started from a fresh, separate clone of `bod-nula` into its own new
  folder/repo — never by developing directly inside this connected copy.
- Refresh procedure for future updates (manual, triggered by the owner,
  not automated — no tooling built for this yet, per P15, until the
  manual process actually proves painful): (1) confirm `agentCodex` is
  clean and its tests pass; (2) copy the framework/governance layer from
  `agentCodex` into the connected `bod nula` folder, excluding `.git/`,
  `.venv/`, cache directories, `.idea/`, `.env`, and `project/` (which
  stays the empty placeholder in `bod-nula` regardless of what
  `agentCodex`'s own `project/` contains by then); (3) manually reapply
  `bod-nula`'s two deliberate differences from `agentCodex` (the README
  title and this ADR's snapshot-role note), since the copy would otherwise
  overwrite them; (4) the owner reviews the diff and commits/pushes
  `bod-nula` themselves, same as today.

## ADR-021: Root directory decluttered to one entry point; framework code moved into agents/

Per the owner's direction: the repository root should hold exactly one
`.py` file — the one used to open a window onto the architect — with
everything else the framework needs living under `agents/`. The owner
also no longer wants a multi-agent console; going forward they only ever
talk to the architect directly, with the reviewer and programmer working
purely as internal pipeline agents.

- Moved into a new `agents` Python package (new `agents/__init__.py`,
  alongside the existing per-role profile directories
  `agents/architect/`, `agents/reviewer/`, `agents/programmer/`, which are
  data directories, not Python modules, and coexist without conflict):
  `agents/agent.py` (from root `agent.py`), `agents/agent_profile.py`
  (from root `agent_profile.py`, import updated to `from .agent import
  ...`), `agents/contract_workflow.py` (from root `contract_workflow.py`,
  unchanged otherwise), `agents/git_ops.py` (from root `git_ops.py`,
  unchanged).
- Fixed a real bug the move would otherwise have introduced:
  `agent.py`'s `WORKSPACE = Path(__file__).parent.resolve()` assumed the
  file lives at the repository root. Moved one level down into
  `agents/agent.py`, that same expression would have resolved to
  `agents/` instead of the actual project root — silently breaking every
  default (`.env` lookup, agent profile directories, provider `cwd`).
  Fixed to `Path(__file__).parent.parent.resolve()`.
- New `agents/pipeline.py` absorbs `agent_console.py`'s orchestration
  logic verbatim (`create_contract`, `revise_contract`,
  `continue_pipeline`, `run_architecture_review`, `implement_next`,
  `review_next`, `commit_approved_contract`, `print_status`,
  `show_inbox`), plus two new functions: `status_text()` and
  `opening_briefing()`, used to ground the new entry point's opening
  greeting in the real contract queue and the architect's real inbox
  content, rather than a static or guessed greeting (see below).
- `agent_console.py` (multi-agent console: `/chat <agent>` switching,
  direct chat with reviewer/programmer) is retired — no longer part of
  the intended workflow. `example_architect.py` (a pre-pipeline demo
  script) is removed — fully superseded by the real pipeline and the new
  entry point, with no remaining purpose.
- The single root entry point, `chat_architect.py`, is rewritten: creates
  all three agents internally (architect, reviewer, programmer — the
  latter two never exposed for direct chat), sends `opening_briefing()`
  to the architect as its first message so its opening greeting reflects
  real state ("what's on the agenda today" grounded in the actual
  contract queue and inbox, not a guess — see `PRINCIPLES.md` P4/P6),
  then a plain input loop: free text goes straight to the architect;
  `/new`, `/revise`, `/work`, `/review`, `/commit`, `/status`, `/inbox`,
  `/help`, `/exit` remain available alongside the conversation, calling
  into `agents/pipeline.py`.
- Tests updated to the new import paths
  (`agents.agent`, `agents.agent_profile`, `agents.contract_workflow`,
  `agents.git_ops`); `tests/test_agent_console.py`'s tests moved to new
  `tests/test_pipeline.py` (importing `agents.pipeline`), plus one new
  test for `opening_briefing()`. Verified with `py_compile` and a full
  pytest run (24/24 passing), including confirming
  `agents.agent.WORKSPACE` resolves to the true project root after the
  move.
- The connected-folder sandbox cannot delete files (a known limitation —
  see the ADR-013-era note on `git rm`/`mv`). The retired root files
  (`agent.py`, `agent_profile.py`, `contract_workflow.py`, `git_ops.py`,
  `agent_console.py`, `example_architect.py`, `tests/test_agent_console.py`)
  were overwritten with a short redirect note each, pointing here and
  asking the owner to `git rm` them manually.
- This is `agentCodex`-only for now, per the owner's own framing
  ("agentCodex jako vývojové repo") — `bod-nula` is refreshed from this
  state later, following the ADR-020 refresh procedure, once the owner
  judges the project ready to deploy.

## ADR-022: `project/` is the default write scope once it holds real code

The owner asked for a check: once `bod-nula` is cloned for a new project
and `project/` starts holding that project's real code, is it clearly
stated anywhere that contract work is scoped to `project/`, with the
framework/governance layer only in scope when a contract explicitly calls
for it? It was not — three places actually said or implied the opposite:

- `AGENTS.md` said "The working directory is the project root," with no
  mention of `project/` scoping at all.
- `agents/agent_profile.py`'s `build_agent_instructions()` always injects
  "Work across the whole project. Do not limit yourself to your own
  subfolder under `agents/`." into every agent's instructions — read
  guidance that, unqualified, doubles as write guidance.
- `agents/architect/ROLE.md` had no scoping statement either, and its
  "Allowed memory targets" list was already stale (missing
  `PRINCIPLES.md`, added to the actual `ALLOWED_MEMORY_TARGETS` code list
  back in ADR-014 but never propagated here).

Fixed, owner confirmed ("ano"):

- `AGENTS.md`: replaced the "working directory is the project root" line
  with an explicit rule — once `project/` holds real code, contract work
  is implemented there by default; touching `agents/*.py`,
  `chat_architect.py`, or a governance `.md` file (`AGENTS.md`,
  `PRINCIPLES.md`, `ROLE.md`, `COMMANDS.md`) is in scope only when the
  contract explicitly calls for it; reading outside `project/` for
  context stays unrestricted — this is a write scope, not a read scope.
  When in doubt, a change outside `project/` gets its own contract point
  rather than silent inclusion.
- `agents/agent_profile.py`: reworded the always-injected "Technical
  profile" text to split reading (unrestricted, across the whole project)
  from writing (scoped to `project/` by default, per the same rule as
  above), so every agent gets this in its instructions regardless of
  role.
- `agents/architect/ROLE.md`: added `PRINCIPLES.md` to "Allowed memory
  targets", matching the code.

Verified: `py_compile` on the touched `.py` files, and a full pytest run
(24/24 passing; had to pass `--confcutdir=tests` to route around the
still-unreadable `.pytest-tmp` directory at the repo root — see the open
git thread below, unrelated to this change).

## ADR-023: `login_claude()` failed to trigger login on a fresh clone

The owner's first real run of a `bod-nula` clone (`chat_architect.py` on a
brand-new project, before ever running `claude auth login`) crashed instead
of prompting for login:

```
RuntimeError: Could not verify Claude login status: {
  "loggedIn": false,
  "authMethod": "none",
  "apiProvider": "firstParty"
}
```

Root cause: `agents/agent.py::login_claude()` treated any non-zero exit
code from `claude auth status --json` as a failure to check status at all,
raising immediately without looking at stdout. In practice the CLI exits
non-zero for the ordinary "not logged in" case too, while still printing
valid JSON with `loggedIn: false` — confirmed by running the command
directly (`claude auth status --json` → exit 1, valid JSON body). So the
one case the function exists to handle (a brand-new machine, nobody has
run `claude auth login` yet) was exactly the case it crashed on instead of
walking the owner through login.

Fixed: `login_claude()` no longer branches on the exit code. It parses
`stdout` and only trusts the result if it is a JSON object containing a
`loggedIn` key (regardless of exit code) — `loggedIn: true` returns
immediately, `loggedIn: false` (or missing/absent) falls through to the
existing `claude auth login --claudeai` flow. Only a body that is empty or
does not parse as that shape is treated as a real failure to verify status
(covers an actual CLI crash, a changed output format, etc.).

Added `tests/test_agent.py` (new file, none existed for this module
before) covering all four paths via a monkeypatched `_run_claude_cli`:
already logged in; not logged in with non-zero exit (the bug's exact
scenario) triggering and completing the login flow; unparseable/empty
status output raising with the original detail; and the login flow itself
failing. Full suite: 28/28 passing.

This is a framework-layer bug (`agents/agent.py`), not project code, so it
was fixed directly here rather than treated as light-path — changes
behavior, and light-path is explicitly for changes that do not (see
`AGENTS.md`). Synced to `bod-nula` the same way as the ADR-021/ADR-022
refresh, since every future clone hits this exact code path on its very
first run. The owner's already-cloned project needs the same one-function
patch applied by hand, since that folder is not connected here.

## ADR-024: Architect must not narrate contract actions it cannot perform

First real end-to-end test of a `bod-nula` clone (project "SMS pro
brány") surfaced a serious gap: the owner discussed a contract with the
architect in plain conversation and said "posíláme dál" (let's send it
on). The architect replied as if it had actually created
`IMPLEMENTATION_CONTRACT_0001.md`, set it to `DRAFT`, and handed it off
to `reviewer` for architecture review — complete with a restated JSON
payload. None of that happened. No contract file was ever written, and
`reviewer` was never invoked. The owner correctly noticed the pipeline
looked "stuck" — there was nothing to be stuck, because nothing had
started.

Root cause: contract creation only happens through
`agents/pipeline.py::create_contract()`, which the host application
(`chat_architect.py`) runs only when the owner types `/new <topic>` (or
`/revise <n> <topic>`) — a code path entirely separate from plain
conversation (`architect.ask(raw)`, used for everything else typed at the
prompt). The architect's own instructions (`agents/architect/ROLE.md`)
correctly stated that "the contract is created by the host application
from your structured JSON proposal," but never said this only happens via
that specific command, nor forbade the model from claiming the action had
already happened during ordinary chat. The architect also runs with
`review` permissions (`Read`, `Grep`, `Glob` only — see its `config.json`)
and has no tool of any kind to create a file or invoke Python itself, so
it was structurally impossible for it to have actually done what it
described; it only generated text that looked like the real output.

Fixed: added an explicit role boundary to `agents/architect/ROLE.md` —
the architect cannot create, submit, revise, or advance a contract during
plain conversation; if the owner agrees a contract should be drafted, it
must tell them to run `/new <topic>` (or `/revise <n> <topic>`), and must
not describe a contract as created, submitted, or under review unless it
was actually invoked through that command this turn.

Not yet done, flagged for a follow-up decision: this only stops the
model from *narrating* the gap away — it does not close the gap itself.
The owner still has to notice the "stuck" pipeline, recognize what
happened, and manually type `/new` with the same task description to
actually start it for real (which is what unblocks the "SMS pro brány"
project, per the owner's own next turn). Worth considering later: should
plain conversation be able to trigger `create_contract()` directly (e.g.
by having the architect emit a recognizable structured signal that
`chat_architect.py` parses out of an otherwise free-text reply), so the
owner does not need to know the `/new` command exists at all — this was
the original point of grounding the opening greeting and having a single
conversational entry point in the first place (ADR-021).

Synced to `bod-nula` — every future clone's architect needs this
boundary from its first session, since this exact scenario (owner agrees
to something in conversation, expects it to actually happen) is the
normal way the architect is meant to be used now.

## ADR-025: Plain conversation can trigger the pipeline for real

Follow-up to ADR-024, decided directly on the owner's live test project
("SMS pro brány"). The owner confirmed the ADR-024 diagnosis (`/status`
showed "No contracts yet", as predicted) but rejected stopping at "the
architect tells you to type `/new`" — the explicit goal, in the owner's
own words: "nebylo nutné znát jednotlivé příkazy, ale aby jejich použití
vyplynulo z konverzace" (no need to know the individual commands — their
use should follow naturally from the conversation). Asked which pipeline
actions should be conversation-triggered; the owner pointed out that the
post-implementation commit was already supposed to be automatic once
owner and architect agree the result is good — tracing back to the
original git-logic request behind ADR-019, where the `CONTRACT_XXXX -
IMPLEMENTED` commit was meant to fire "pokud se shodneme na tom, že je
dostatečná" (once we agree it's sufficient), not only via an explicit
`/commit`. So the scope is the three moments that are naturally decided
*in conversation*: drafting a contract, revising one, and agreeing an
approved implementation is good to ship. `/work` and `/review` stay
manual-override only — the pipeline already auto-chains through them
(ADR-018), so there is no conversational decision point for them to hang
off of.

Mechanism: the architect ends a reply with a trailing fenced
` ```pipeline-action ` block containing JSON — `{"action": "create",
"task": "..."}`, `{"action": "revise", "number": N, "task": "..."}`, or
`{"action": "commit", "number": N}` — only when the owner has just given
clear, explicit agreement (see the new "Triggering the pipeline from
conversation" section added to `agents/architect/ROLE.md`, spelling out
exactly when and how). `agents/pipeline.py` gained two new functions:
`extract_pipeline_action()` (regex-extracts and JSON-parses a trailing
block, stripping it from what the owner sees; returns `(text, None)`
unchanged if no valid block is present — never raises) and
`dispatch_pipeline_action()` (routes a parsed action to the existing
`create_contract` / `revise_contract` / `commit_approved_contract`, which
already do the real work — this is purely a new way to invoke them,
not new pipeline logic). `chat_architect.py`'s free-text branch now
calls both after every `architect.ask(raw)`, before printing, and prints
the real pipeline output afterward (created/reviewed/committed status
lines) exactly as `/new` etc. already did — so the owner sees the actual
system response, not just the architect's prose, closing the loop ADR-024
started (never claim, always show what really happened).

The slash commands themselves are unchanged and still work as manual
overrides (e.g. if the owner wants to force a contract without
back-and-forth, or the architect fails to emit the block). `/status`,
`/inbox`, `/help`, `/exit`, `/work`, `/review` are untouched.

Added 8 new tests to `tests/test_pipeline.py` covering
`extract_pipeline_action` (no block, valid block, malformed JSON, missing
`action` key) and `dispatch_pipeline_action` (create, commit, unknown
action — must not raise). Full suite: 35/35 passing.

Applied directly to the "SMS pro brány" project (owner's explicit
request, to tune the pipeline there before porting the result back — an
authorized exception to the ADR-022 project/-scoping default, not a
violation of it): `agents/agent.py` there already had the ADR-023 fix
(that project was cloned from `bod-nula` after that fix landed); synced
`agents/architect/ROLE.md`, `agents/pipeline.py`, `chat_architect.py`,
and `tests/test_pipeline.py` directly (framework files, no reason for
per-project drift), and added local ADR-024/ADR-025 entries to that
project's own `memory/DECISIONS.md` rather than overwriting it, since its
memory is independent of this repository's from the point it was cloned
(see ADR-020). Synced to `bod-nula` the same way once validated, so every
future clone starts with this already working.

## ADR-026: Resume a contract left mid-pipeline by an interrupted session

Surfaced on "SMS pro brány" again: the owner created a contract, it was
handed off to `programmer`, and the station restarted before the
implementation finished. The next session showed the contract correctly
stuck at `READY_FOR_PROGRAMMER`, but nothing moved it forward — the owner
had to notice and ask. Worse, when asked to "hand it to the programmer
again," the architect (correctly recognizing it has no tool to do that
itself) told the owner they needed to "open a session for the
`programmer` agent" — which is not how this application works.
`chat_architect.py` already creates the `architect`, `reviewer`, and
`programmer` agents together in one process (`ExitStack` in `main()`);
there is no separate "programmer session" to open. The real fix was
already sitting unused in the owner's own hands: the manual-override
`/work` command, in the very session they were already in.

The owner asked whether this calls for a new `orchestrator` role. Decided
against it: resuming a stalled contract is a deterministic lookup — "is
anything sitting at `READY_FOR_PROGRAMMER` or `READY_FOR_ARCHITECT_REVIEW`
that isn't normally supposed to stay there?" — not a judgment call an LLM
needs to make. `ContractStore.next_for_programmer()` /
`next_for_implementation_review()` already answer exactly that. Adding an
agent to decide something a few lines of plain code already decide
correctly would just be new surface area for the same class of bug this
ADR is about (an agent describing pipeline mechanics it doesn't actually
control). Asked the owner how proactive the resume should be; picked
"ask, then continue" over "resume silently" or "report only, leave it to
a command" — consistent with `/commit` staying a deliberate owner
checkpoint rather than a silent side effect.

Added to `agents/pipeline.py`: `find_stuck_contracts()` (contracts sitting
in `READY_FOR_PROGRAMMER` or `READY_FOR_ARCHITECT_REVIEW` — states that
are normally transient within a single `continue_pipeline()` call, so
surviving into a new session means the previous run didn't finish, not
that anyone is waiting on the owner) and `resume_stuck_contract()`
(picks up with `implement_next()`/`review_next()` from wherever the
contract actually is, same as `continue_pipeline()` would have).
`opening_briefing()` now calls `find_stuck_contracts()` and, if anything
is found, explicitly instructs the architect to flag it and ask the owner
before doing anything. `dispatch_pipeline_action()` gained a fourth
action, `"resume"` (alongside `create`/`revise`/`commit` from ADR-025),
routed to `resume_stuck_contract()`. `agents/architect/ROLE.md`'s
"Triggering the pipeline from conversation" section documents this fourth
action and states plainly that the architect must not claim a separate
session or agent is needed — the programmer is already live in the same
conversation.

Added 7 new tests to `tests/test_pipeline.py`
(`find_stuck_contracts` filtering correctly vs. genuine owner checkpoints,
`opening_briefing`'s stuck-note appearing/not appearing,
`resume_stuck_contract` from both stuck statuses and as a no-op on a
non-stuck one, and `dispatch_pipeline_action` routing `"resume"`). Full
suite: 42/42 passing.

Synced to `bod-nula` and to "SMS pro brány" the same way as ADR-025 (the
owner needs this working in the live session where the problem actually
occurred). Restarting "SMS pro brány"'s `chat_architect.py` is required
for the fix to take effect, same caveat as ADR-025.

## ADR-027: Reviews must check code against the declared minimum runtime version, not just what's installed locally

Generalizes a finding from reviewing "SMS pro brány"'s actual application
code (project-specific, not itself brought into this repository —
`project/` here stays empty; only the process lesson generalizes).
`project/send_sms.py` there used a backslash inside an f-string
expression, valid only from Python 3.12 onward (PEP 701), while
`project/pyproject.toml` declared `requires-python = ">=3.11"`. On 3.10 or
3.11 the module is a hard `SyntaxError` at import — not a runtime bug,
the code cannot even be loaded. Both the architecture review and two
rounds of implementation review across two separate contracts missed it,
because the programmer's own local interpreter was newer than the
declared floor, its tests genuinely passed there, and nobody checked
"passed under what version, and does that match what we declared to
support."

This is a process gap independent of any one project's code, so it
belongs in the role instructions rather than in any project's `project/`
tree. Added to `agents/programmer/ROLE.md`'s "Way of working": when a
project declares a minimum supported language/runtime version, do not
rely on whatever is locally available — check new syntax/stdlib usage is
actually valid at that declared floor, and report which
interpreter/runtime version tests actually ran under, so it's checkable.
Added a matching line to `agents/architect/commands/review_contract.md`:
during implementation review, do not accept passing tests at face value
if the report doesn't state what version they ran under.

Deliberately kept lightweight (a sentence in each of two existing files,
no new mandatory step, no tooling) rather than, say, requiring every
contract to run tests under every declared-supported version — that
would be process weight disproportionate to how often this actually
bites (P14). Docs-only change; full suite still 42/42 (no test file
touched). Synced to `bod-nula` and "SMS pro brány" the same way as
ADR-023 through ADR-026.

## ADR-028: Pipeline steps print their actual content, not just a status line

Another live finding on "SMS pro brány": after `continue_pipeline()` (or
`/work`, `/review`, `resume_stuck_contract()`) ran the programmer and then
the architect's implementation review automatically, the console showed
only `IMPLEMENTATION_CONTRACT_0003 handed off to the architect for
review.` and `IMPLEMENTATION_CONTRACT_0003: APPROVED; handed off to
owner.` — terse status lines. The actual review content (what was
checked, why it passed) only appeared once the owner explicitly asked
"jak vypadá výsledek?" The owner asked for this to happen automatically.

Root cause: `run_architecture_review()`, `implement_next()`, and
`review_next()` in `agents/pipeline.py` all parse a JSON response
containing real prose (`findings` from the reviewer, `summary` from the
programmer and from the architect's implementation review) purely to
extract fields for `ContractStore` — the prose itself was discarded after
that, never shown to the owner. The one-line status print was the only
output, regardless of how much substance the actual review contained.
This is the same class of gap as ADR-024/ADR-025 from the other
direction: there it was the architect describing an action nobody asked
it to narrate; here it's the host application doing real work and
narrating none of it.

Fixed: all three functions now print the real content (`findings` /
`summary`) immediately after their existing status line — no new
mechanism, no new agent call, the text was already being fetched and
parsed, just not shown. This applies uniformly whether the step was
reached via `/work`, `/review`, the ADR-025 conversational actions, or
ADR-026's `resume_stuck_contract()` — none of them are special-cased.

Docs/code-only change to three `print()` calls; no test asserted on
console output before this, so nothing to update; full suite still
42/42. Synced to `bod-nula` and "SMS pro brány" the same way as ADR-023
through ADR-027.

## ADR-029: Governance `.md` files moved into `agents/`; entry point renamed to `main.py`

Owner's direction: the repository root should hold only `README.md`,
`requirements.txt`, `.gitignore`, `.env`, `.env.example`, and the single
entry point — renamed from `chat_architect.py` to `main.py`. Everything
else agent-related moves into `agents/`, continuing the ADR-021
consolidation (framework code already lives there; the governing
documentation now sits next to it instead of at the root).

Asked the owner where exactly the four root `.md` files should land,
since `AGENTS.md` and `PRINCIPLES.md` are functionally wired into code
(`agent_profile.py` reads `PRINCIPLES.md` by a fixed path; it is also one
of the three patterns in `ALLOWED_MEMORY_TARGETS`) while
`AGENTS_SUGGESTIONS.md` and `UPDATE_NOTES.md` are reference/historical
notes — a split was one reasonable option. Owner chose putting all four
under `agents/` uniformly.

Moved: `AGENTS.md` → `agents/AGENTS.md`, `PRINCIPLES.md` →
`agents/PRINCIPLES.md`, `AGENTS_SUGGESTIONS.md` →
`agents/AGENTS_SUGGESTIONS.md`, `UPDATE_NOTES.md` → `agents/UPDATE_NOTES.md`.
`chat_architect.py` → `main.py` (content otherwise unchanged — it never
referenced its own filename).

Code changes required by the move (the two places `PRINCIPLES.md` was
functionally wired to a root-relative path, not just mentioned in prose):
- `agents/agent_profile.py`: `principles_file` now resolves to
  `project_root / "agents" / "PRINCIPLES.md"`.
- `agents/contract_workflow.py`: `ALLOWED_MEMORY_TARGETS`'s pattern is now
  `^agents/PRINCIPLES\.md$` (was `^PRINCIPLES\.md$`); the matching error
  message updated to match.
- `agent_profile.py`'s always-injected "Technical profile" text (ADR-022)
  and every prose reference to `AGENTS.md`/`PRINCIPLES.md` across
  `agents/architect/ROLE.md`, `agents/programmer/ROLE.md`,
  `agents/reviewer/ROLE.md`/`COMMANDS.md`/`commands/architecture_review.md`,
  `README.md`, `project/README.md`, and `memory/PROJECT_STATE.md` updated
  to the new `agents/` paths. `memory/DECISIONS.md`'s own historical ADR
  entries are left untouched — an append-only log describes what was true
  when it was written, not what is true now.
- Two tests updated to match: `tests/test_agent_profile.py` writes the
  fixture's `PRINCIPLES.md` to `agents/PRINCIPLES.md`;
  `tests/test_contract_workflow.py`'s allowed-target test now uses
  `agents/PRINCIPLES.md`.

The five retired root files (`AGENTS.md`, `PRINCIPLES.md`,
`AGENTS_SUGGESTIONS.md`, `UPDATE_NOTES.md`, `chat_architect.py`) were
overwritten with short redirect notes, same as every previous retirement
in this repository (ADR-021) — the connected-folder sandbox cannot delete
files, so the owner deletes them manually. Root now holds exactly
`README.md`, `requirements.txt`, `.gitignore`, `.env`, `.env.example`, and
`main.py`, once those five are removed.

Verified: `py_compile` on all touched `.py` files, full pytest run (42/42
passing). Synced to `bod-nula` and "SMS pro brány" the same way as
ADR-023 through ADR-028 — both need the same five-file move, the same two
code edits, and the same `main.py` rename, plus their own five old-root
files retired the same way. "SMS pro brány" needs `main.py` (not
`chat_architect.py`) run from now on, and its `.venv`/IDE run
configuration updated accordingly by the owner.

## ADR-030: Read-only Streamlit status dashboard

The owner proposed a frontend where each of the three pipeline roles gets
its own visible area showing what it is currently working on, floated
giving the `programmer` a "ask for clarification when unsure" behavior
with a way to answer it directly in its own window. Discussed before
building anything (P11 — validate on the smallest real case first):

- Whether this replaces the architect-only conversational entry point
  from ADR-021, or is a separate, optional, read-only view running
  alongside `main.py` — owner confirmed: for now, an optional add-on; the
  live-chat-with-any-agent idea is explicitly deferred, not decided
  against.
- Where the interactive "ask for clarification" idea would actually need
  to land: `programmer` today runs as a single blocking `run_command()`
  call and returns one final JSON result — pausing mid-task to ask a
  question would need a new contract status (something like "waiting on
  the owner") and a way to resume afterward. Real scope, deliberately not
  built yet.
- What a *read-only* first version can show at all: no agent's
  conversation is logged anywhere today — only the final structured
  result of a `run_command()` call is ever persisted, inside the contract
  file itself. So "what is X currently doing" can only mean "the last
  thing X wrote to disk," not a live, turn-by-turn feed. Owner confirmed
  this is fine for a first version; logging every `ask()`/`run_command()`
  call is a separate, later decision, not a prerequisite.
- Where the code should live: root holds exactly one `.py` file per
  ADR-029 (`main.py`). Since this first version has no chat window and
  does not run or drive the pipeline, it did not need to become a second
  root entry point — `agents/dashboard.py`, run via `streamlit run
  agents/dashboard.py`, keeps the root-cleanliness rule intact. If a live
  chat window is built later, this placement is worth revisiting then,
  not now.

Built: `agents/pipeline.py` gained two new pure, testable functions —
`inbox_text()` (extracted from `show_inbox()`, which now uses it too, so
the same logic isn't duplicated) and `role_snapshot(store)` (returns
`{"architect": [...], "reviewer": [...], "programmer": [...]}`, each a
list of `Contract`s currently handed off to that role, via the existing
`list_contracts(assigned_to=...)` — no new query logic, just grouping
what already existed by role). `agents/dashboard.py` is a new Streamlit
script: a contract-queue table, then one column per role showing its
contracts (status, handoff, and the latest available note — the last
implementation review summary, or architecture review findings, or
programmer point note, in that order of recency) and that role's inbox.
A "Refresh" button reruns the script; no background thread, no polling,
no new dependency on the framework's own agent code beyond what
`main.py` already imports. Added `streamlit` to `requirements.txt`.

The script inserts the repository root onto `sys.path` itself before
importing `agents.*`, since Streamlit executes it directly rather than as
part of the `agents` package (same reasoning as project-level test
`conftest.py` files needing to do the same for their own package).

Added 6 new tests to `tests/test_pipeline.py` (`inbox_text` for a
missing/present agent inbox and the owner inbox path;
`role_snapshot` grouping correctly by current handoff, and returning
empty lists for an empty queue). Full suite: 47/47 passing. Manually
smoke-tested `streamlit run agents/dashboard.py` (headless) against both
an empty contract queue and "SMS pro brány"'s real queue — starts and
serves without a server-side exception in either case.

Synced to `bod-nula` and "SMS pro brány" the same way as ADR-021 through
ADR-029.
