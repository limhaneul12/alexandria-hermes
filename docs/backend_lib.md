# Alexandria-Hermes Backend Library Surface

This document replaces the original backend MVP prompt. The active product is a local-first, agent-facing library and Context Vault for Hermes/Alexandria recall. It is not a human CMS or a generic archive platform.

## Current product boundary

Alexandria-Hermes keeps the write path agent-native:

```text
Hermes/agent/MCP/API capture
→ durable library/context storage
→ search/recall/RAG Context Pack
→ optional librarian collaboration
→ human curation after save
```

Humans operate the library as curators. The supported human-facing UI shape is browse, search, inspect, archive, delete, and lightweight cleanup. Human pre-save review queues and direct CMS-style authoring screens are intentionally outside the core UI.

## Core library objects

Active public library/context material is organized around:

- `SKILL`: reusable capability or procedure saved by agent/self-acquisition flows.
- `PROMPT`: reusable instruction artifact saved by agent-facing prompt submission flows.
- `CONTEXT` / `MEMORY COMPACT`: durable decisions, handoffs, compact summaries, and project context stored in Context Vault.
- `HARNESS`: read-only execution evidence/context kind for completed agent work when captured through agent/MCP paths.

Historical item kinds and import/provider surfaces that were removed from core should stay documented in migration notes or pruning contracts, not in live onboarding/API docs.

## Active backend surfaces

### Library and Context Vault

- list/search/get/update/archive/delete library items for curation;
- submit agent-authored skills and prompts through agent-facing routes/tools;
- capture, recall, search, archive, and inspect contexts;
- prepare and browse memory compacts;
- record usage events for retrieval quality and future recommendations.

### Librarian collaboration

The librarian is optional collaboration, not the default recall path. Multiple librarian profiles/providers are supported so an operator can route different requests to different helper agents or models. Provider credentials remain backend-side; browser/client surfaces must not expose raw secrets.

### MCP and CLI

The MCP server and CLI call the same backend contracts. MCP is the primary agent-facing integration path. CLI commands are useful for local operation, smoke tests, and setup, but they must not reintroduce removed human approval queues or stale CMS-shaped create/review screens.

## Removed or non-core surfaces

The following are not active core product surfaces:

- Capture Review pre-save screen;
- human approval queue for agent-submitted candidates;
- generic object-storage import bridge;
- legacy dedicated library item CRUD families that duplicate current item/context surfaces;
- direct human authoring pages for skills/prompts/context.

If one of these capabilities becomes necessary again, design it as a plugin/importer or agent-owned capture path with a dedicated contract and migration story instead of reusing historical draft text.

## Verification guidance

When pruning or restoring a backend surface:

1. Add or update a negative contract test first.
2. Confirm the test fails for the stale surface.
3. Remove route/schema/service/frontend/docs exposure.
4. Run focused contracts, then the GitHub Actions parity pre-push hook.
5. Leave historical references only in migration files, pruning contracts, or dated implementation notes where they explain compatibility.
