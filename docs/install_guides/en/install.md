# Alexandria-Hermes Install Guide

## 1. Summary

Alexandria-Hermes is a **single-operator, local-first SQLite** companion for Hermes Agent. It lets Hermes search, recall, and submit durable context, skills, prompts, and knowledge candidates when local/current context is not enough.

- SQLite is the supported default database. There is no PostgreSQL runtime choice.
- Full-stack mode is a first-class supported path, not a demo-only path.
- If you only need backend + DB for Hermes/agent usage, prefer `backend-daemon` over Docker Compose.
- If an agent performs the install for a user, it must ask for the runtime mode before writing files.

## 2. Choose a runtime mode

| Mode | Use when | Runtime |
| --- | --- | --- |
| `fullstack-compose` | you want backend + frontend together | Docker Compose |
| `fullstack-separate` | you run backend/frontend as local development processes | `uvicorn` + `npm run dev` |
| `backend-daemon` | Hermes only needs backend + SQLite, no UI | local daemon under `~/.hermes/alexandria-hermes/` |
| `guidebook-only` | the agent should only create docs/checklists | documentation only |

If delegating to an agent, ask first:

```text
Which runtime mode do you want: fullstack-compose / fullstack-separate / backend-daemon / guidebook-only?
```

## 3. Install the CLI/MCP binary

### Git install with uv tool

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git#subdirectory=backend"
alexandria-hermes --help
```

To pin a release tag:

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git@v0.1.0#subdirectory=backend"
```

### Local clone smoke check

```bash
git clone https://github.com/limhaneul12/alexandria-hermes.git
cd alexandria-hermes/backend
uv sync
uv run alexandria-hermes --help
```

## 4. Run the application runtime

### A. fullstack-compose

Run from the repository root.

```bash
set -a
[ -f .env ] && . ./.env
set +a

export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-${SERVICE_OPERATOR_API_KEY:-}}"

docker compose up --build backend frontend
```

Verify:

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
```

### B. fullstack-separate

Terminal 1 — backend:

```bash
cd backend
uv sync
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/alexandria_hermes.db}" uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm run security:npm-supply-chain
npm run dev
```

Terminal 3 — health:

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
```

### C. backend-daemon

Recommended when there is no UI requirement.

```bash
alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
alexandria-hermes daemon install --dry-run --json
alexandria-hermes serve --env-file ~/.hermes/alexandria-hermes/.env --host 127.0.0.1 --port 8000
```

Before installing an OS service, inspect the `--dry-run` service file and env file paths.

## 5. Onboard Hermes assets and MCP

Run this after the backend is available.

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-}"

alexandria-hermes --json hermes onboard \
  --hermes-home "$HERMES_HOME" \
  --api-url "$ALEXANDRIA_API_URL" \
  --operator-api-key "${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --install-prompts \
  --install-mcp
```

`~/.hermes/alexandria-hermes/mcp-config.json` is only a snippet. Hermes discovers native MCP tools from `mcp_servers` in `~/.hermes/config.yaml`.

```bash
ALEXANDRIA_CLI="$(command -v alexandria-hermes)"

hermes mcp add alexandria \
  --command "$ALEXANDRIA_CLI" \
  --args mcp serve \
  --env ALEXANDRIA_API_URL="$ALEXANDRIA_API_URL" \
  --env ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --env HERMES_HOME="$HERMES_HOME"

hermes mcp test alexandria
```

Restart Hermes CLI/Gateway/Discord sessions after MCP config changes.

## 6. Smoke test

Do not stop at install proof. Verify both health and Hermes integration:

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
alexandria-hermes --json hermes doctor --hermes-home "$HERMES_HOME" --api-url "$ALEXANDRIA_API_URL"
```

Then start a fresh Hermes session and confirm Alexandria tools are visible, usually with names such as `mcp_alexandria_*`. For prior-project memory, Hermes should use local/current context first, then current Memory Compact, then Context Vault recall/RAG.

## 7. Policy on/off

The default policy is ON.

```bash
alexandria-hermes hermes policy status
alexandria-hermes hermes policy disable
alexandria-hermes hermes policy enable
```

Policy file:

```text
~/.hermes/alexandria-hermes/policy.yaml
```

## 8. Security and exposure notes

- The operator key is not a user login token; it protects control-plane operations.
- Never paste real secrets/API keys/tokens into docs or logs.
- Default runtime examples assume localhost/private operator access.
- Before LAN/public exposure, add VPN, reverse-proxy auth, firewall allowlists, or SSH tunneling.

## 9. Troubleshooting

| Symptom | Check |
| --- | --- |
| `alexandria-hermes` is missing | `uv tool list`, `command -v alexandria-hermes` |
| health fails | backend/daemon is running and `ALEXANDRIA_API_URL` is correct |
| MCP snippet exists but Hermes has no tools | run `hermes mcp add/test alexandria`, then restart Hermes |
| provider/settings route returns 401/403 | pass `ALEXANDRIA_OPERATOR_API_KEY` / service env correctly |
| Compose feels unnecessary without UI | use `backend-daemon` mode |
