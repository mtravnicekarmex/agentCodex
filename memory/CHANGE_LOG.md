# Change Log

Log of small fixes made without a contract (light path, see `AGENTS.md`
section "Light path for small fixes"). One line per fix: what, where, by
whom. Contract changes are not logged here — those have their own history
directly in `contracts/IMPLEMENTATION_CONTRACT_NNNN.md`.

Never deleted or overwritten — only a new entry is added.

- 2026-07-28: `agents/architect/commands/review_contract.md` — added an
  explicit instruction to also check the contract's `# Architecture Review`
  section (the reviewer's findings) during implementation review, not only
  the original point text. By Claude, during the PRINCIPLES.md migration
  (P10).
- 2026-07-28: `agents/programmer/ROLE.md` and
  `agents/programmer/commands/implement_contract.md` — added an explicit
  instruction to report a real architectural gap in a point's note instead
  of deciding it, rather than only covering "blocked". By Claude, during
  the PRINCIPLES.md migration (P13).
- 2026-07-28: `.gitignore` — added `.pytest-tmp/` and `.idea/` (previously
  flagged in the first review, revision point 1-2, and deferred); untracked
  the 6 already-committed `.idea/*` files via `git rm --cached` so they
  stop propagating into every project cloned from this repo as "point
  zero". `.pytest-tmp/` was not tracked in this particular checkout, so
  only the `.gitignore` entry was needed here — the fix was verified
  against a separate clone (`bod-nula`) where `.pytest-tmp/` was tracked
  with 25 leftover files; that clone needs the same `git rm --cached -r
  .pytest-tmp` applied directly. By Claude, checking `bod-nula`'s clonability.
