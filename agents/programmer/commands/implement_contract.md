Implement this contract:

File: {{CONTRACT_PATH}}

Content:
<contract>
{{CONTRACT_CONTENT}}
</contract>

Make actual changes to the source files. When done, return only valid
JSON:

{
  "summary": "implementation summary",
  "notes": [
    {
      "point": 1,
      "note": "what was concretely done",
      "files": ["agent.py"],
      "tests": ["python -m pytest -v — 8 passed"]
    }
  ],
  "tests": [
    "an overall test or check"
  ]
}

Rules:
- notes must contain exactly one entry for every point of the contract,
- the point numbers must match the contract,
- list only files actually changed and tests actually run,
- if something cannot be finished, describe the blocker truthfully; do
  not present a point as done,
- if a point requires a decision the contract does not make, do not
  invent one — implement only what is unambiguous, describe the gap in
  that point's note, and mention it in the overall summary.
