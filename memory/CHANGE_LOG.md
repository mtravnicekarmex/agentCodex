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
