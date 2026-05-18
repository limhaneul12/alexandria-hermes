## Summary

-

## Impacted areas

- [ ] Backend / API
- [ ] CLI / MCP
- [ ] Frontend UI
- [ ] Context Vault / RAG
- [ ] Memory Compacts
- [ ] Library skills/prompts
- [ ] Librarian delegation
- [ ] Install / Docker / CI
- [ ] Documentation

## Validation

Paste the exact commands you ran and the result.

```text
# example
cd backend && make ci
cd frontend && npm run security:npm-supply-chain && npm run lint && npm run build
```

## Security / privacy checklist

- [ ] I did not commit raw API keys, operator keys, OAuth tokens, provider secrets, private keys, or full unredacted conversation logs.
- [ ] I used placeholders such as `[REDACTED]` or `<operator-key>` in docs, tests, and examples.
- [ ] Browser-facing code does not expose operator keys, provider secrets, or OAuth token material.
- [ ] Any protected control-plane call uses the operator-key model, not a login/session/RBAC assumption.

## Product positioning checklist

- [ ] The change preserves Alexandria-Hermes as a local-first agent-native library/control plane.
- [ ] The change does not reposition the project as an autonomous agent runtime, prompt marketplace, MCP marketplace, or generic hosted memory API.
- [ ] User-facing copy avoids raw backend routes, frontend paths, source ids, or internal identifiers unless the user explicitly asked for API details.

## Risk / rollback notes

- Risk:
- Rollback:
