Run implementation review on this contract — AFTER implementation, against
the Acceptance Criteria of each point (as opposed to architecture review,
which assesses the contract itself before implementation):

File: {{CONTRACT_PATH}}

Contract content:
<contract>
{{CONTRACT_CONTENT}}
</contract>

Read the actual changed source files and tests. Check every point of the
contract. You did not run the contract's architecture review yourself —
also read the `# Architecture Review` section (the reviewer's rounds and
findings) so you check the implementation against what was actually
accepted, not only the original point text in isolation; if the reviewer's
findings clarified or narrowed a point, that clarification is part of the
requirement. If the project declares a minimum supported language/runtime
version (e.g. `requires-python`), do not accept the programmer's test
results at face value if they do not state what version those tests
actually ran under — new code passing on a newer local interpreter can
still be a hard syntax error on the declared minimum (see ADR-027).
Return only valid JSON:

{
  "approved": true,
  "summary": "overall review",
  "reviews": [
    {
      "point": 1,
      "status": "APPROVED",
      "review": "concrete findings and verification"
    }
  ],
  "memory_updates": [
    {
      "path": "memory/DECISIONS.md",
      "text": "a permanent, verified finding"
    },
    {
      "path": "agents/programmer/MEMORY.md",
      "text": "a finding important for the programmer's future work"
    }
  ]
}

Rules:
- a review must exist for every point,
- status is only APPROVED or CHANGES_REQUESTED,
- approved may only be true when every point is APPROVED,
- memory_updates may be an empty list,
- do not store the whole contract or temporary details in memory.
