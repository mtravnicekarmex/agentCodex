# Current Project State

The project provides a shared synchronous API for Codex and Claude threads.
It now also includes a higher-level agent layer that loads a profile from
`agents/<name>/` and continues to use the existing `create_thread()` as its
technical foundation.

The framework/governance layer (`agent.py`, `agent_profile.py`,
`contract_workflow.py`, `git_ops.py`, the pipeline orchestration
`pipeline.py`, and the governance docs `AGENTS.md`/`PRINCIPLES.md`/
`AGENTS_SUGGESTIONS.md`/`UPDATE_NOTES.md`) lives under the `agents/`
package, alongside the per-role profile directories (`agents/architect/`,
`agents/reviewer/`, `agents/programmer/`). The repository root has
exactly one `.py` file, `main.py` — a single window onto the architect;
the reviewer and programmer are created internally to run the pipeline
but are not chatted with directly. On start, the architect is briefed
with the real contract queue and its own inbox before its first greeting,
and flagged if anything is stuck mid-pipeline from an interrupted session
(see ADR-021, ADR-026, ADR-029).
