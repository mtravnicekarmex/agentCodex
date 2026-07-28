# Current Project State

The project provides a shared synchronous API for Codex and Claude threads.
It now also includes a higher-level agent layer that loads a profile from
`agents/<name>/` and continues to use the existing `create_thread()` as its
technical foundation.
