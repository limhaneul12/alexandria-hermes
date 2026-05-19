# Alexandria Operating Loop

Use Alexandria only when it improves grounding.

1. Check whether Alexandria usage is enabled. If policy contains `enabled: false`, stay silent about Alexandria unless the user asks.
2. For local/current context, prefer `mcp_alexandria_alexandria_recall_context` or `mcp_alexandria_alexandria_search`.
3. If MCP is not available, use CLI fallback such as `alexandria-hermes context recall`.
4. For missing skills, use Hermes-alone self-acquisition fallback before librarian delegation.
5. Ask a librarian only when the user explicitly requests librarian collaboration.

Never store secrets. Keep captures concise and durable.
