---
name: alexandria-library
description: Use when current/local Hermes context, memory, skills, prompts, or librarian-backed self-acquisition may help the task, especially when agents must read or safely update scoped Obsidian-backed memory without overwriting another agent.
---

# Alexandria Library

Use Alexandria as an optional local-first knowledge library for Hermes.

## When to use
- Search local/current context before asking the user to repeat prior decisions.
- When local/current context is insufficient, read the current Memory Compact
  before deeper Context Vault recall/RAG.
- Recall project decisions, compact handoffs, skill candidates, prompts, and usage notes.
- Acquire a missing skill through Hermes-alone fallback first; ask a librarian only on explicit user request.

## Policy contract
- Check `~/.hermes/alexandria-hermes/policy.yaml` or run `alexandria-hermes hermes policy status` before assuming Alexandria is enabled.
- If the policy says `enabled: false`, do not use Alexandria unless the user asks to turn it back on.
- Users can opt out with `alexandria-hermes hermes policy disable` and re-enable with `alexandria-hermes hermes policy enable`.
- Librarian delegation is optional and should require explicit user request.

## Status/diagnostics
- Use `alexandria-hermes hermes doctor` for local status/diagnostics.
- Prefer MCP tools named `mcp_alexandria_*` when available.
- If MCP is unavailable, fall back to CLI commands such as
  `alexandria-hermes memory-compacts current`,
  `alexandria-hermes context recall`, or backend API calls.

## Operating style
- Treat Alexandria as a helper, not an obligation.
- Long-term memory lookup order: current conversation and Hermes local memory
  first, then current Memory Compact, then Context Vault recall/RAG, then
  library skill/prompt search, then Hermes self-acquisition.
- Treat librarian delegation as separate from memory lookup; use a librarian only
  on explicit user request or stricter local policy.
- Keep writes compact and durable: decisions, root causes, reusable plans, and skill candidates.
- Do not store secrets, transient task logs, or private credentials.

## Safe Agent writes

Treat every update as a read-modify-write operation:

1. Read the current note and retain its `content_hash`.
2. Preserve its stable `id`, canonical path, and applicable scope identity.
3. Send the current hash as `expected_content_hash` when replacing the note.
4. If the backend returns `409 OBSIDIAN_WRITE_CONFLICT`, do not retry blindly.
5. Re-read the note, merge the newer content, and retry with the new hash.

An atomic file replacement prevents partial Markdown, but `expected_content_hash`
prevents one agent from silently overwriting another agent's completed update.

## Scope identity

- `AGENT` writes and recall require the intended `agent_id`.
- `SESSION` writes and recall require the intended `session_id`.
- `PROJECT` writes and recall require the intended `project`.
- Supply `workspace_id` whenever the caller has one.
- Do not broaden a missing identity to `GLOBAL`; fail closed and repair the request.
- Keep each concurrent task on its own database/request session.

After canonical writes, verify the note can be read back and that scoped
FTS/vector/HYBRID recall does not return another agent, session, project, or
workspace.
