# Use Alexandria Library

When a task references prior work, project decisions, local skills, prompts, or durable context, use Alexandria as an optional local-first library.

Preferred order:
1. Respect `alexandria-hermes hermes policy status` and `enabled: false`.
2. Use `mcp_alexandria` tools when present.
3. Fall back to `alexandria-hermes context recall`, `alexandria-hermes library`, or HTTP APIs only when needed.
4. Keep librarian delegation optional and tied to explicit user request.

If Alexandria is disabled or unavailable, continue with normal Hermes tools without blocking the user.
