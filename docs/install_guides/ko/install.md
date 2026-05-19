# Alexandria-Hermes 설치 가이드

## 1. 한 줄 요약

Alexandria-Hermes는 Hermes Agent가 장기 컨텍스트, 스킬, 프롬프트, 후보 지식을 로컬 우선으로 검색/저장할 수 있게 해주는 **single-operator, local-first SQLite** companion다.

- 기본 DB는 SQLite다. PostgreSQL 선택지는 없다.
- Full-stack은 데모가 아니라 정상 지원 경로다.
- UI가 필요 없고 Hermes/agent가 backend + DB만 쓰면 Docker Compose 대신 `backend-daemon`이 자연스럽다.
- 설치를 agent에게 위임했다면 agent는 파일을 쓰기 전에 runtime mode를 먼저 물어야 한다.

## 2. Runtime mode 선택

| Mode | 언제 쓰나 | 실행 방식 |
| --- | --- | --- |
| `fullstack-compose` | backend + frontend를 한 번에 띄우고 싶을 때 | Docker Compose |
| `fullstack-separate` | backend/frontend를 각각 로컬 개발 프로세스로 띄울 때 | `uvicorn` + `npm run dev` |
| `backend-daemon` | UI 없이 Hermes가 backend + SQLite만 쓰면 될 때 | `~/.hermes/alexandria-hermes/` local daemon |
| `guidebook-only` | 실행 파일은 쓰지 않고 안내/검증 자료만 만들 때 | 문서만 생성 |

Agent에게 설치를 맡겼다면 먼저 이렇게 답하게 한다.

```text
원하는 runtime mode를 골라주세요: fullstack-compose / fullstack-separate / backend-daemon / guidebook-only
```

## 3. CLI/MCP binary 설치

### uv tool로 Git 설치

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git#subdirectory=backend"
alexandria-hermes --help
```

Release tag를 고정하려면:

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git@v0.1.0#subdirectory=backend"
```

### 로컬 clone에서 확인

```bash
git clone https://github.com/limhaneul12/alexandria-hermes.git
cd alexandria-hermes/backend
uv sync
uv run alexandria-hermes --help
```

## 4. Application runtime 실행

### A. fullstack-compose

repo root에서 실행한다.

```bash
set -a
[ -f .env ] && . ./.env
set +a

export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-${SERVICE_OPERATOR_API_KEY:-}}"

docker compose up --build backend frontend
```

확인:

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
```

### B. fullstack-separate

터미널 1 — backend:

```bash
cd backend
uv sync
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/alexandria_hermes.db}" uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

터미널 2 — frontend:

```bash
cd frontend
npm run security:npm-supply-chain
npm run dev
```

터미널 3 — health:

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
```

### C. backend-daemon

UI 없이 Hermes companion처럼 쓸 때 권장한다.

```bash
alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
alexandria-hermes daemon install --dry-run --json
alexandria-hermes serve --env-file ~/.hermes/alexandria-hermes/.env --host 127.0.0.1 --port 8000
```

운영체제 서비스로 설치할 때는 먼저 `--dry-run` 출력의 service file과 env file 경로를 확인한 뒤 적용한다.

## 5. Hermes onboard + MCP 등록

Backend가 떠 있는 상태에서 실행한다.

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

`~/.hermes/alexandria-hermes/mcp-config.json`은 snippet이다. 실제 Hermes tool discovery는 `~/.hermes/config.yaml`의 `mcp_servers` 등록을 사용한다.

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

설정 후 Hermes CLI/Gateway/Discord 세션을 새로 시작하거나 재시작한다.

## 6. Smoke test

Health만 보지 말고 최소 기능을 확인한다.

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
alexandria-hermes --json hermes doctor --hermes-home "$HERMES_HOME" --api-url "$ALEXANDRIA_API_URL"
```

그 다음 Hermes 세션에서 Alexandria MCP tool이 보이는지 확인한다. 보통 `mcp_alexandria_*` 형태로 노출된다.

## 7. Policy on/off

기본값은 ON이다.

```bash
alexandria-hermes hermes policy status
alexandria-hermes hermes policy disable
alexandria-hermes hermes policy enable
```

Policy 파일 위치:

```text
~/.hermes/alexandria-hermes/policy.yaml
```

## 8. 보안/노출 주의

- operator key는 로그인 토큰이 아니라 control-plane 보호용 단일 운영자 키다.
- secret/API key/token은 문서나 로그에 실제 값으로 남기지 않는다.
- 기본 실행은 localhost/private operator 전제다.
- LAN/public 노출 전에는 VPN, reverse proxy auth, firewall allowlist, SSH tunnel 중 하나 이상을 둔다.

## 9. Troubleshooting

| 증상 | 확인 |
| --- | --- |
| `alexandria-hermes` 명령이 없음 | `uv tool list`, `command -v alexandria-hermes` |
| health 실패 | backend/daemon이 떠 있는지, `ALEXANDRIA_API_URL`이 맞는지 확인 |
| MCP snippet은 있는데 Hermes tool이 안 보임 | `hermes mcp add/test alexandria` 후 Hermes 재시작 |
| provider/settings route가 401/403 | `ALEXANDRIA_OPERATOR_API_KEY` 또는 service env 전달 확인 |
| UI가 필요 없는데 Compose가 부담됨 | `backend-daemon` mode 사용 |
