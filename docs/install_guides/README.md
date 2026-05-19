# Alexandria-Hermes Install Guides

This directory is the split, language-specific install guidebook for Alexandria-Hermes.

## Benchmark notes from oh-my-codex README

The install guide structure intentionally borrows the parts of the oh-my-codex onboarding docs that reduce agent/user confusion:

1. **Recommended default flow first** — put the happy path before advanced modes.
2. **Prerequisites before commands** — separate CLI install prerequisites from runtime prerequisites.
3. **Runtime proof, not only install proof** — include `doctor`/health checks plus a real feature smoke test.
4. **Mental model section** — explain what the tool is and is not before command maps.
5. **Execution mode map** — show mode choices up front so an agent asks before writing files.
6. **Command map + troubleshooting** — group setup, daemon, Hermes MCP, policy, and smoke-test commands.
7. **State directory contract** — explain durable local state (`~/.hermes/alexandria-hermes/`) explicitly.
8. **Manual setup refresh** — avoid hidden side effects; install commands should not silently launch application runtimes.

## Language guides

| Language | Guide | Audience |
| --- | --- | --- |
| 한국어 | [ko/install.md](ko/install.md) | primary project/operator guide |
| English | [en/install.md](en/install.md) | OSS users and external agents |
| 简体中文 | [zh/install.md](zh/install.md) | Chinese-language operators/agents |
| 日本語 | [ja/install.md](ja/install.md) | Japanese-language operators/agents |

## Structure contract

Every language guide follows this order:

1. What Alexandria-Hermes is
2. Choose a runtime mode
3. Install the CLI/MCP binary
4. Run the application runtime
5. Onboard Hermes assets and MCP
6. Verify with health + context capture/recall smoke tests
7. Toggle policy on/off
8. Security and exposure notes
9. Troubleshooting checklist

## Runtime modes

| Mode | Use when | Runtime |
| --- | --- | --- |
| `fullstack-compose` | backend + frontend should run together with Docker Compose | Docker Compose services |
| `fullstack-separate` | frontend and backend are developed/run as local processes | `uvicorn` + `npm run dev` |
| `backend-daemon` | Hermes/agent only needs backend + SQLite, no UI | local daemon under `~/.hermes/alexandria-hermes/` |
| `guidebook-only` | an agent should write docs/checklists but not create runtime files | documentation only |

If an agent is installing for a user, it must ask for one of these modes before applying files.

## SQLite-only contract

Alexandria-Hermes is local-first and uses SQLite for the supported default deployment path. Do not add a PostgreSQL choice to the install flow unless the application actually adds and tests that support later.
