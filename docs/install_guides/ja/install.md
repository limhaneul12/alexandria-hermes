# Alexandria-Hermes インストールガイド

## 1. 概要

Alexandria-Hermes は Hermes Agent のための **single-operator / local-first / SQLite** companion です。Hermes が現在の会話やローカル memory だけでは足りないとき、context、skill、prompt、knowledge candidate を検索・保存・再利用できるようにします。

- サポートされる標準 DB は SQLite です。PostgreSQL の選択肢はありません。
- Full-stack は demo-only ではなく、正式なサポート経路です。
- Hermes/agent が backend + DB だけを使い、UI が不要な場合は Docker Compose ではなく `backend-daemon` が自然です。
- agent にインストールを任せる場合、agent はファイルを書き込む前に runtime mode を確認する必要があります。

## 2. Runtime mode を選ぶ

| Mode | 使う場面 | Runtime |
| --- | --- | --- |
| `fullstack-compose` | backend + frontend をまとめて起動したい | Docker Compose |
| `fullstack-separate` | backend/frontend をローカル開発プロセスとして別々に起動したい | `uvicorn` + `npm run dev` |
| `backend-daemon` | Hermes が backend + SQLite だけを必要とし、UI は不要 | `~/.hermes/alexandria-hermes/` 配下の local daemon |
| `guidebook-only` | 実行ファイルは作らず、ドキュメント/チェックリストだけ作る | documentation only |

agent に任せる場合は先にこう確認します。

```text
runtime mode を選んでください: fullstack-compose / fullstack-separate / backend-daemon / guidebook-only
```

## 3. CLI/MCP binary をインストールする

### uv tool で Git install

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git#subdirectory=backend"
alexandria-hermes --help
```

release tag を固定する場合:

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git@v0.1.0#subdirectory=backend"
```

### ローカル clone で確認

```bash
git clone https://github.com/limhaneul12/alexandria-hermes.git
cd alexandria-hermes/backend
uv sync
uv run alexandria-hermes --help
```

## 4. Application runtime を起動する

### A. fullstack-compose

repo root で実行します。

```bash
set -a
[ -f .env ] && . ./.env
set +a

export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-${SERVICE_OPERATOR_API_KEY:-}}"

docker compose up --build backend frontend
```

確認:

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

UI が不要な場合の推奨経路です。

```bash
alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
alexandria-hermes daemon install --dry-run --json
alexandria-hermes serve --env-file ~/.hermes/alexandria-hermes/.env --host 127.0.0.1 --port 8000
```

OS service として実際に登録する前に、`--dry-run` の service file と env file のパスを確認してください。

## 5. Hermes onboard + MCP 登録

backend が起動している状態で実行します。

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

`~/.hermes/alexandria-hermes/mcp-config.json` は snippet です。Hermes の実際の MCP tool discovery は `~/.hermes/config.yaml` の `mcp_servers` 登録を使います。

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

MCP 設定を変更した後は Hermes CLI/Gateway/Discord session を再起動してください。

## 6. Smoke test

インストール確認だけで止めず、runtime と Hermes integration を確認します。

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
alexandria-hermes --json hermes doctor --hermes-home "$HERMES_HOME" --api-url "$ALEXANDRIA_API_URL"
```

その後、新しい Hermes session を開始し、`mcp_alexandria_*` のような Alexandria MCP tools が見えることを確認します。

## 7. Policy on/off

デフォルト policy は ON です。

```bash
alexandria-hermes hermes policy status
alexandria-hermes hermes policy disable
alexandria-hermes hermes policy enable
```

Policy file:

```text
~/.hermes/alexandria-hermes/policy.yaml
```

## 8. Security / exposure notes

- operator key は user login token ではなく、control-plane 操作を守るための key です。
- 本物の secret/API key/token を docs や logs に残さないでください。
- 既定の例は localhost/private operator を前提にしています。
- LAN/public に公開する前に VPN、reverse-proxy auth、firewall allowlist、SSH tunnel のいずれかを用意してください。

## 9. Troubleshooting

| 症状 | 確認 |
| --- | --- |
| `alexandria-hermes` が見つからない | `uv tool list`, `command -v alexandria-hermes` |
| health が失敗する | backend/daemon が起動しているか、`ALEXANDRIA_API_URL` が正しいか |
| MCP snippet はあるが Hermes に tools が出ない | `hermes mcp add/test alexandria` 後に Hermes を再起動 |
| provider/settings route が 401/403 | `ALEXANDRIA_OPERATOR_API_KEY` / service env の渡し方を確認 |
| UI 不要で Compose が重い | `backend-daemon` mode を使う |
