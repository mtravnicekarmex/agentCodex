Prepare a contract for the programmer for this request:

{{TASK}}

Do not implement code. Study the relevant files and return only valid JSON,
with no additional commentary:

{
  "title": "short title",
  "purpose": "why we are making this change — the architectural intent, for a human",
  "intent": "what the implementation deliberately addresses and deliberately does not; how it relates to the existing architecture",
  "current_state": "briefly, what exists in the repository today and what the change touches",
  "inputs": "what the implementation builds on (existing modules, API, data)",
  "outputs": "what the implementation creates or changes (files, public API)",
  "out_of_scope": "what this change explicitly does not address (SHALL NOT)",
  "future_evolution": "what is deliberately deferred to later, so the implementation does not try to cover it now",
  "points": [
    {
      "assignment": "concrete requirement (SHALL)",
      "acceptance_criteria": [
        "verifiable criterion 1",
        "verifiable criterion 2"
      ]
    }
  ]
}

Rules:
- "purpose" and "intent" belong to humans — architectural rationale, not a
  technical description; "points" belong to implementation — a precise,
  testable specification. Never mix these two layers.
- the points must be actionable in order,
- every point must have a clearly verifiable result,
- include tests and documentation as separate points when needed,
- do not include vague phrasing like "as needed",
- if `{{TASK}}` is only about editing an existing contract after
  CHANGES_REQUESTED from architecture review, take the stated findings
  into account and return the complete, rewritten content (not just a
  diff).
