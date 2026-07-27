---
name: operational-sync
description: Use when Alexandria-Hermes needs encrypted operational backup, isolated restore verification, SQLite/Obsidian index synchronization, embedding soft rebuild, RAG status repair, stale cache cleanup, or proof that the library is READY/HYBRID.
---

# Operational Sync

Use this skill to restore Alexandria-Hermes retrieval health without modifying Obsidian Markdown source notes.

## Invariants

- Treat Obsidian Markdown as the source of truth.
- Treat SQLite, FTS, vector, and embedding rows as rebuildable cache/index state.
- Prefer non-destructive sync first: status check → Obsidian reindex → embedding soft rebuild → readiness verification.
- Create a verified operational backup before manual SQLite cleanup or recovery.
- Restore into an isolated drill directory before considering maintenance recovery.
- Never hard-delete Obsidian Markdown as part of this procedure.
- Never overwrite the live Vault directly from a browser request.
- Stop only when `/operations/readiness` is `READY` or the remaining blocker is explicitly explained.

## Fast path

Run from the repo root unless noted otherwise.

```bash
curl -sS http://127.0.0.1:8000/health/live
curl -sS http://127.0.0.1:8000/obsidian/status | jq
curl -sS http://127.0.0.1:8000/memory/contexts/rag/status | jq
curl -sS http://127.0.0.1:8000/operations/readiness | jq
```

If `stale_notes>0` or the vault index may be stale:

```bash
curl -sS -X POST http://127.0.0.1:8000/obsidian/index/rebuild | jq
```

If `embedding=REINDEX_REQUIRED`, `stale_rows>0`, or `missing_rows>0`:

```bash
curl -sS -X POST \
  "http://127.0.0.1:8000/memory/contexts/retrieval/soft-rebuild?limit=1000&verification_query=운영%20안정성%20자동%20복구%20루프&project=alexandria-hermes" | jq
```

After every reindex, re-check RAG status. Vault reindex can create new missing embedding rows, so run soft rebuild again if needed.

## Encrypted backup and restore drill

Create a local encrypted backup:

```bash
backup_json="$(
  curl -fsS -X POST http://127.0.0.1:8000/operations/backups
)"
printf '%s\n' "$backup_json" | jq
backup_id="$(printf '%s' "$backup_json" | jq -r '.backup_id')"
```

The published manifest must report schema version `2` and encryption `fernet`.
The local key is stored separately under the configured backup root and must
never be copied into Obsidian, logs, reports, or a portable backup bundle.

Run a non-destructive restore drill:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8000/operations/backups/${backup_id}/restore-drill" | jq
```

Require:

- all manifest artifacts verified;
- `sqlite_integrity=HEALTHY` when SQLite artifacts exist;
- restored files remain under `.restore-drills`;
- live Vault and live SQLite files remain unchanged.

`SERVICE_OPERATIONAL_BACKUP_RETENTION_COUNT` controls how many successfully
published backups are retained. Pruning occurs only after a new backup has been
verified and published.

## Maintenance recovery boundary

Use the existing recovery plan/run workflow for live maintenance. Do not turn a
restore drill into an unguarded live copy.

1. Create and verify an encrypted backup.
2. Run the restore drill and inspect its report.
3. Inspect the recovery dry-run plan.
4. Start maintenance recovery only when the plan allows automatic execution.
5. Let the recovery lock serialize mutation, quarantine existing SQLite state,
   rebuild schema/indexes, and verify readiness.
6. Stop only after `READY/HYBRID`, or preserve the failed run manifest and report
   the exact blocker.

## Manual stale cache cleanup

Only use this when all remaining `obsidian_files.index_status='stale'` rows refer to Markdown files that no longer exist in the vault.

1. Inspect stale rows and related derived rows.
2. Create and verify an encrypted operational backup.
3. Delete stale `obsidian_files` rows and related `obsidian_edges`; `obsidian_chunks` should cascade from `obsidian_files`.
4. Run `PRAGMA foreign_key_check`.
5. Verify `/obsidian/status`, `/memory/contexts/rag/status`, and `/operations/readiness`.

The direct file copy below is only a secondary same-host safety snapshot after
the operational backup succeeds:

```bash
backup="backend/data/alexandria_hermes.pre-stale-cache-clean-$(date -u +%Y%m%dT%H%M%SZ).db"
cp backend/data/alexandria_hermes.db "$backup"
echo "$backup"
```

Cleanup:

```bash
sqlite3 backend/data/alexandria_hermes.db <<'SQL'
PRAGMA foreign_keys=ON;
BEGIN IMMEDIATE;
CREATE TEMP TABLE stale_note_ids(note_id TEXT PRIMARY KEY);
INSERT INTO stale_note_ids(note_id)
SELECT note_id FROM obsidian_files WHERE index_status='stale';
DELETE FROM obsidian_edges
WHERE source_note_id IN (SELECT note_id FROM stale_note_ids)
   OR target_note_id IN (SELECT note_id FROM stale_note_ids);
DELETE FROM obsidian_files WHERE note_id IN (SELECT note_id FROM stale_note_ids);
COMMIT;
PRAGMA foreign_key_check;
SQL
```

## Final verification

Readiness must be clean:

```bash
curl -sS http://127.0.0.1:8000/operations/readiness | jq
```

Expected:

```json
{
  "status": "READY",
  "ready": true,
  "warnings": [],
  "blockers": [],
  "next_actions": []
}
```

Run a representative HYBRID search:

```bash
curl -sS -X POST http://127.0.0.1:8000/memory/contexts/retrieval/search \
  -H "Content-Type: application/json" \
  --data '{"query":"운영 안정성 자동 복구 루프","strategy":"HYBRID","limit":3,"project":"alexandria-hermes"}' | jq
```

Expected:

- `effective_strategy=HYBRID`
- no warnings
- a relevant Obsidian PRD/context note appears
- vector/semantic retrieval evidence is present

## Code repair note

If `/operations/readiness` returns 500 with a Pydantic validation error for `ContextEmbeddingSourceStatusResponse`, fix the interface schema boundary rather than the embedding data:

- Convert `ContextEmbeddingSourceStatus` dataclasses through `source_status_payload()` before Pydantic validation.
- Add/keep a router regression test that asserts `rag.source_statuses` is serialized.
- Run `cd backend && make ci` before claiming completion.
