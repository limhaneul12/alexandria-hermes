---
name: alexandria-library
description: Use when current/local Hermes context, memory, skills, prompts, or librarian-backed self-acquisition may help the task.
---

# Alexandria Library

Use Alexandria as an optional local-first knowledge library for Hermes.

## When to use
- Search local/current context before asking the user to repeat prior decisions.
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
- If MCP is unavailable, fall back to CLI commands such as `alexandria-hermes context recall` or backend API calls.

## Operating style
- Treat Alexandria as a helper, not an obligation.
- Keep writes compact and durable: decisions, root causes, reusable plans, and skill candidates.
- Do not store secrets, transient task logs, or private credentials.
