# Hermes Install & Apply Guide

## 목적

이 문서는 Hermes에게 그대로 전달할 수 있는 Alexandria-Hermes 설치/적용 **입구 문서**다.
상세 절차는 언어별 install guidebook으로 분리했다.

- 한국어: [docs/install_guides/ko/install.md](docs/install_guides/ko/install.md)
- English: [docs/install_guides/en/install.md](docs/install_guides/en/install.md)
- 简体中文: [docs/install_guides/zh/install.md](docs/install_guides/zh/install.md)
- 日本語: [docs/install_guides/ja/install.md](docs/install_guides/ja/install.md)
- 구조/벤치마크: [docs/install_guides/README.md](docs/install_guides/README.md)

목표는 Hermes runtime이 Alexandria-Hermes를 **CLI와 native MCP tool**로 사용할 수 있게 만들고,
처음 설치한 사용자도 Hermes가 **로컬/현재 컨텍스트를 먼저 사용한 뒤, 부족할 때 Alexandria를 자연스럽게 쓰고** 원하면 명확히 끌 수 있게 하는 것이다.
장기기억 탐색은 현재 대화/Hermes local memory 다음에 **current Memory Compact → Context Vault recall/RAG** 순서로 이어진다.

## 핵심 주의점

- Alexandria-Hermes는 **no-login, single-operator, local-first** 시스템이다.
- 기본 온보딩에는 회원가입/로그인, GPT/Codex OAuth, provider credential이 필요하지 않다.
- Alexandria application secret은 `ALEXANDRIA_OPERATOR_API_KEY` 하나뿐이다. 이것은 사용자 로그인 토큰이 아니라 settings/provider/OAuth/librarian delegation 같은 control-plane 작업을 보호하는 단일 운영자 키다.
- Alexandria-Hermes는 지원 경로에서 **SQLite local DB**를 사용한다. PostgreSQL mode나 DB 선택지는 제공하지 않는다.
- Full-stack은 demo-only가 아니라 정상 지원 경로다.
- UI 없이 Hermes/agent가 backend + DB만 활용한다면 Docker Compose가 필수는 아니다. `backend-daemon` mode를 사용한다.
- `alexandria-hermes hermes onboard --install-mcp`가 만드는 `~/.hermes/alexandria-hermes/mcp-config.json`은 설치 산출물/snippet이다.
- Hermes Agent가 실제로 MCP 서버를 자동 발견하려면 `~/.hermes/config.yaml`의 `mcp_servers.alexandria`에 merge되어 있어야 한다.
- MCP tool discovery는 Hermes/Gateway 시작 시점에 일어난다. 설정 후에는 새 세션 또는 Gateway 재시작이 필요하다.
- secret/API key/token 값은 문서/로그에 실제 값으로 남기지 않는다.

## Agent 설치 위임 시 runtime mode 먼저 질문

Hermes/agent가 이 설치를 대신 수행한다면 파일을 쓰기 전에 반드시 사용자에게 원하는 runtime mode를 먼저 물어본다.

```text
원하는 runtime mode를 골라주세요: fullstack-compose / fullstack-separate / backend-daemon / guidebook-only
```

| Mode | 언제 쓰나 | 실행 방식 |
| --- | --- | --- |
| `fullstack-compose` | backend + frontend를 Docker Compose로 함께 실행 | Docker Compose |
| `fullstack-separate` | backend/frontend를 각각 로컬 프로세스로 실행 | `uvicorn` + `npm run dev` |
| `backend-daemon` | UI 없이 backend + SQLite만 Hermes local companion처럼 실행 | `~/.hermes/alexandria-hermes/` local daemon |
| `guidebook-only` | 실행 파일은 쓰지 않고 안내/검증 자료만 생성 | 문서만 생성 |

## 빠른 적용 흐름

객관적인 실행 순서는 아래처럼 잡는다.

1. **CLI/MCP binary 설치**
2. **Application runtime 실행** — `fullstack-compose`, `fullstack-separate`, `backend-daemon` 중 선택
3. **CLI health 확인**
4. **Hermes onboard + MCP 등록**
5. **Hermes MCP discovery 확인**
6. **Context capture/recall 같은 최소 기능 smoke test**

## CLI 설치

```bash
uv tool install "git+https://github.com/limhaneul12/alexandria-hermes.git#subdirectory=backend"
alexandria-hermes --help
```

로컬 clone 검증:

```bash
git clone https://github.com/limhaneul12/alexandria-hermes.git
cd alexandria-hermes/backend
uv sync
uv run alexandria-hermes --help
```

## Runtime 실행 요약

### fullstack-compose

```bash
set -a
[ -f .env ] && . ./.env
set +a

export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-${SERVICE_OPERATOR_API_KEY:-}}"

docker compose up --build backend frontend
```

### fullstack-separate

Backend:

```bash
cd backend
uv sync
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/alexandria_hermes.db}" uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run security:npm-supply-chain
npm run dev
```

### backend-daemon

```bash
alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
alexandria-hermes daemon install --dry-run --json
alexandria-hermes serve --env-file ~/.hermes/alexandria-hermes/.env --host 127.0.0.1 --port 8000
```

## Hermes onboard + MCP 등록 요약

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

ALEXANDRIA_CLI="$(command -v alexandria-hermes)"
hermes mcp add alexandria \
  --command "$ALEXANDRIA_CLI" \
  --args mcp serve \
  --env ALEXANDRIA_API_URL="$ALEXANDRIA_API_URL" \
  --env ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --env HERMES_HOME="$HERMES_HOME"

hermes mcp test alexandria
```

설정 후 Hermes CLI/Gateway/Discord 세션을 재시작한다.

## 검증

```bash
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health
alexandria-hermes --json hermes doctor --hermes-home "$HERMES_HOME" --api-url "$ALEXANDRIA_API_URL"
alexandria-hermes --json hermes policy status --hermes-home "$HERMES_HOME"
```

성공 기준:

- backend health가 정상이다.
- `skill_installed: true`
- `mcp_config_installed: true`
- `policy_installed: true`
- policy `enabled: true`
- 새 Hermes session에서 Alexandria MCP tools가 노출된다. 보통 `mcp_alexandria_*` 형태다.

## Policy on/off

기본값은 Alexandria 사용 ON이다.

```bash
alexandria-hermes hermes policy status
alexandria-hermes hermes policy disable
alexandria-hermes hermes policy enable
```

Policy 파일:

```text
~/.hermes/alexandria-hermes/policy.yaml
```

## 더 자세한 문서

- 처음 설치/온보딩 전체 절차: [docs/install_guides/ko/install.md](docs/install_guides/ko/install.md)
- 기능별 사용 가이드북: [docs/usage_guidebook/README.md](docs/usage_guidebook/README.md)
- MCP runtime 차이: [docs/usage_guidebook/mcp_runtime/mcp_runtime_guide_01.md](docs/usage_guidebook/mcp_runtime/mcp_runtime_guide_01.md)
- Policy on/off: [docs/usage_guidebook/hermes_policy/hermes_policy_guide_01.md](docs/usage_guidebook/hermes_policy/hermes_policy_guide_01.md)
- Troubleshooting: [docs/usage_guidebook/troubleshooting/troubleshooting_guide_01.md](docs/usage_guidebook/troubleshooting/troubleshooting_guide_01.md)
