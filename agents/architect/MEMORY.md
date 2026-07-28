# Long-Term Memory: Architect Agent

## Project purpose

The `agentCodex` project provides a thin synchronous layer over the
OpenAI Codex SDK and the Anthropic Claude Agent SDK. Both providers should
share as unified a public interface as possible for a long-lived
conversational thread.

## Current public API

- `create_thread(provider, model, reasoning, permission_profile, config=...)`
- `create_agent(agent_name, config=..., project_root=...)`
- `ask(text)`
- `close()`
- context manager

## Important principles

- `create_thread()` is the low-level technical layer.
- `create_agent()` loads the role, memory, working state, and commands.
- All agents work over a shared project root.
- Specific models live in `.env`; the agent profile uses the `low`, `mid`,
  `high` levels.
- Short-term memory lives in the active thread.
- Long-term memory lives in Markdown files.
- Runtime data must not be confused with versioned memory.

## Current limitations

- Thread persistence and resumption are not implemented yet.
- `persistent_thread` is a prepared configuration option for a later stage.
- The architect uses the default `review` profile, so it does not change
  files.
