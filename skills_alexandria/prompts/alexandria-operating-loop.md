# Alexandria Operating Loop

Use Alexandria only when it improves grounding.

1. Check whether Alexandria usage is enabled. If policy contains `enabled: false`, stay silent about Alexandria unless the user asks.
2. For ordinary work, first use current conversation, Hermes local memory, loaded skills, and local files.
3. Long-term memory lookup order: read the current Memory Compact, then use Context Vault recall/RAG for the specific gap, then search library skills/prompts when reusable assets may matter.
4. Prefer `mcp_alexandria_alexandria_get_current_memory_compact`, `mcp_alexandria_alexandria_recall_context`, `mcp_alexandria_alexandria_rag_context`, or `mcp_alexandria_alexandria_search` when available.
5. If MCP is not available, use CLI fallback such as `alexandria-hermes memory-compacts current` before `alexandria-hermes context recall`.
6. For missing skills, use Hermes-alone self-acquisition fallback before librarian delegation.
7. Ask a librarian only when the user explicitly requests librarian collaboration; librarian delegation is separate from memory lookup.

Never store secrets. Keep captures concise and durable.
