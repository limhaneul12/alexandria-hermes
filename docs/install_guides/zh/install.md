# Alexandria-Hermes 安装指南

## 1. 概要

Alexandria-Hermes 是 Hermes Agent 的 **single-operator、local-first、SQLite** companion。它让 Hermes 在当前/本地上下文不足时，可以检索、召回、保存 context、skill、prompt 和知识候选项。

- 支持的默认数据库是 SQLite。安装流程不提供 PostgreSQL 选项。
- Full-stack 不是 demo-only，而是正式支持路径。
- 如果只需要给 Hermes/agent 使用 backend + DB，不需要 UI，推荐 `backend-daemon`，不必强制 Docker Compose。
- 如果把安装交给 agent，agent 在写文件前必须先询问 runtime mode。

## 2. 选择 runtime mode

| Mode | 适用场景 | 运行方式 |
| --- | --- | --- |
| `fullstack-compose` | backend + frontend 一起运行 | Docker Compose |
| `fullstack-separate` | backend/frontend 分别作为本地开发进程运行 | `uvicorn` + `npm run dev` |
| `backend-daemon` | Hermes 只需要 backend + SQLite，不需要 UI | `~/.hermes/alexandria-hermes/` 下的本地 daemon |
| `guidebook-only` | agent 只生成文档/检查清单，不创建运行文件 | 仅文档 |

委托 agent 安装时，先让它提问：

```text
请选择 runtime mode: fullstack-compose / fullstack-separate / backend-daemon / guidebook-only
```

## 3. 安装 CLI/MCP binary

### 使用 uv tool 从 Git 安装

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git#subdirectory=backend"
alexandria-hermes --help
```

固定 release tag：

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git@v0.1.0#subdirectory=backend"
```

### 本地 clone 验证

```bash
git clone https://github.com/limhaneul12/alexandria-hermes.git
cd alexandria-hermes/backend
uv sync
uv run alexandria-hermes --help
```

## 4. 运行 application runtime

### A. fullstack-compose

在 repo root 执行：

```bash
set -a
[ -f .env ] && . ./.env
set +a

export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-${SERVICE_OPERATOR_API_KEY:-}}"

docker compose up --build backend frontend
```

验证：

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
```

### B. fullstack-separate

终端 1 — backend:

```bash
cd backend
uv sync
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/alexandria_hermes.db}" uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

终端 2 — frontend:

```bash
cd frontend
npm run security:npm-supply-chain
npm run dev
```

终端 3 — health:

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
```

### C. backend-daemon

没有 UI 需求时推荐使用：

```bash
alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
alexandria-hermes daemon install --dry-run --json
alexandria-hermes serve --env-file ~/.hermes/alexandria-hermes/.env --host 127.0.0.1 --port 8000
```

真正安装 OS service 前，先检查 `--dry-run` 输出中的 service file 和 env file 路径。

## 5. Hermes onboard + MCP 注册

确认 backend 已运行后执行：

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

`~/.hermes/alexandria-hermes/mcp-config.json` 只是 snippet。Hermes 真正的 MCP tool discovery 读取 `~/.hermes/config.yaml` 中的 `mcp_servers`。

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

修改 MCP 配置后，需要重启 Hermes CLI/Gateway/Discord session。

## 6. Smoke test

不要只验证安装文件，还要验证 runtime 和 Hermes 集成：

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
alexandria-hermes --json hermes doctor --hermes-home "$HERMES_HOME" --api-url "$ALEXANDRIA_API_URL"
```

然后开启新的 Hermes session，确认能看到 Alexandria MCP tools，通常名称类似 `mcp_alexandria_*`。

## 7. Policy on/off

默认 policy 是 ON。

```bash
alexandria-hermes hermes policy status
alexandria-hermes hermes policy disable
alexandria-hermes hermes policy enable
```

Policy 文件：

```text
~/.hermes/alexandria-hermes/policy.yaml
```

## 8. 安全与暴露边界

- operator key 不是用户登录 token，而是 control-plane 操作保护 key。
- 不要把真实 secret/API key/token 写进文档或日志。
- 默认示例假设 localhost/private operator 使用。
- 暴露到 LAN/public 前，请先配置 VPN、reverse-proxy auth、firewall allowlist 或 SSH tunnel。

## 9. Troubleshooting

| 症状 | 检查项 |
| --- | --- |
| 找不到 `alexandria-hermes` | `uv tool list`, `command -v alexandria-hermes` |
| health 失败 | backend/daemon 是否运行，`ALEXANDRIA_API_URL` 是否正确 |
| 有 MCP snippet 但 Hermes 没有 tools | 运行 `hermes mcp add/test alexandria` 后重启 Hermes |
| provider/settings route 返回 401/403 | 正确传入 `ALEXANDRIA_OPERATOR_API_KEY` / service env |
| 不需要 UI，Compose 太重 | 使用 `backend-daemon` mode |
