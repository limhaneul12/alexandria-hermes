# Hermes Install & Apply Guide

## 목적

이 문서는 Hermes에게 그대로 전달할 수 있는 Alexandria-Hermes 설치/적용 프롬프트다.
목표는 Hermes runtime이 Alexandria-Hermes를 **CLI와 native MCP tool**로 사용할 수 있게 만들고,
처음 설치한 사용자도 Hermes가 **로컬/현재 컨텍스트를 먼저 사용한 뒤, 부족할 때 Alexandria를 자연스럽게 쓰고** 원하면 명확히 끌 수 있게 하는 것이다.

핵심 주의점:

- Alexandria-Hermes는 **no-login, single-operator, local-first** 시스템이다. 기본 온보딩에는
  회원가입/로그인, GPT/Codex OAuth, provider credential이 필요하지 않다.
- Alexandria application secret은 `ALEXANDRIA_OPERATOR_API_KEY` 하나뿐이다. 이것은
  사용자 로그인 토큰이 아니라 settings/provider/OAuth/librarian delegation 같은 control-plane
  작업을 보호하는 단일 운영자 키다.
- `alexandria-hermes hermes onboard`는 `~/.hermes/alexandria-hermes/policy.yaml`을 함께 설치한다.
  이 policy contract의 기본값은 `enabled: true`다.
- 사용자가 원치 않으면 `alexandria-hermes hermes policy disable`로 끄고,
  다시 쓰려면 `alexandria-hermes hermes policy enable`로 켠다.
- 사서(librarian)는 협업/품질 보조자이지 필수 실행 경로가 아니다. 사서가 없어도 Hermes는
  local/current context → local skill → Alexandria search/recall when needed → Hermes self-acquisition → candidate 제출 흐름을 직접 수행할 수 있어야 한다.
- `alexandria-hermes hermes onboard --install-mcp`가 만드는
  `~/.hermes/alexandria-hermes/mcp-config.json`은 **설치 산출물/snippet**이다.
- Hermes Agent가 실제로 MCP 서버를 자동 발견하려면 `~/.hermes/config.yaml`의
  `mcp_servers.alexandria`에 merge되어 있어야 한다.
- MCP tool discovery는 Hermes/Gateway 시작 시점에 일어난다. 설정 후에는 새 세션 또는 Gateway 재시작이 필요하다.
- 테스트나 사용자가 금지한 상황에서는 `alexandria_ask_librarian`, librarian OAuth/job 계열 tool을 호출하지 않는다.
- ChatGPT/Codex OAuth provider가 필요하면 endpoint/client id를 수동 입력하지 않는다. Alexandria UI의 Settings → Librarians → `ChatGPT / Codex OAuth 시작`이 Hermes-compatible 기본값으로 browser authorization을 시작한다.
- repo root `.env`에는 operator key만 있으면 된다. Codex OAuth public metadata는 Hermes처럼 backend 코드 기본값으로 제공되고, `SERVICE_CODEX_OAUTH_*`는 특수 배포 override 용도다.
- provider/settings API는 operator key가 필요하다. Docker Compose는 repo root `.env`의 `SERVICE_OPERATOR_API_KEY`를 backend와 frontend server proxy에 전달한다.
- Docker Compose 기본 포트는 localhost에만 bind된다. LAN/public 노출이 필요하면 VPN, reverse-proxy auth,
  firewall allowlist, SSH tunnel 같은 별도 access boundary를 먼저 둔다.

---

## URL/env 이름 규칙

설치 문서에서는 사람이 읽기 쉬운 변수명으로 `ALEXANDRIA_API_URL`을 사용한다. CLI 전역 `--base-url`의 공식 envvar는 현재 `HERMES_API_URL`이고, MCP backend client는 `ALEXANDRIA_API_URL`과 `HERMES_API_URL`을 모두 허용한다.

권장 운영 방식:

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export HERMES_API_URL="$ALEXANDRIA_API_URL"
```

- CLI 직접 호출: `--base-url "$ALEXANDRIA_API_URL"`를 명시하면 env 이름 차이에 의존하지 않는다.
- Hermes MCP 등록: `ALEXANDRIA_API_URL`을 env로 넘기면 MCP client가 읽는다.
- secret 값은 문서/로그에 실제 값으로 남기지 않는다.

---

## 사용법 가이드북

기능별 사용 예제는 아래 가이드북에 분리했다.

```text
docs/usage_guidebook/
```

파일 규칙은 다음과 같다.

```text
docs/usage_guidebook/<기능폴더>/<기능>_guide_<number>.md
```

현재 포함된 가이드:

- [Install/Onboard](docs/usage_guidebook/install_onboard/install_onboard_guide_01.md)
- [Hermes Policy ON/OFF](docs/usage_guidebook/hermes_policy/hermes_policy_guide_01.md)
- [MCP Runtime](docs/usage_guidebook/mcp_runtime/mcp_runtime_guide_01.md)
- [Context Recall Smoke Test](docs/usage_guidebook/context_recall/context_recall_guide_01.md)
- [Memory Compacts Coverage Window](docs/usage_guidebook/memory_compacts/memory_compacts_guide_01.md)
- [Library Assets Search/Full Load](docs/usage_guidebook/library_assets/library_assets_guide_01.md)
- [Self-Acquisition](docs/usage_guidebook/self_acquisition/self_acquisition_guide_01.md)
- [Librarian Collaboration](docs/usage_guidebook/librarian_collaboration/librarian_collaboration_guide_01.md)
- [Security & Privacy](docs/usage_guidebook/security_privacy/security_privacy_guide_01.md)
- [Troubleshooting](docs/usage_guidebook/troubleshooting/troubleshooting_guide_01.md)
- [OSS Onboarding Docs Pattern](docs/usage_guidebook/oss_onboarding/oss_onboarding_guide_01.md)

---

## 0. 처음 설치하는 사람을 위한 빠른 적용 흐름

대부분의 사용자는 이 프로젝트의 배경 대화를 모른 채 “설치하고 바로 Hermes가 쓰게” 만들려고 한다.
따라서 처음 적용할 때는 아래 순서만 지키면 된다.

### 0-1. 한 번에 이해할 핵심

Alexandria-Hermes를 Hermes가 제대로 쓰려면 **세 가지가 모두 필요**하다.

1. Alexandria-Hermes backend가 실행되고 DB migration이 `head`까지 적용되어 있어야 한다.
2. `alexandria-hermes hermes onboard`로 Hermes home에 skill/prompt/MCP snippet을 설치해야 한다.
3. `~/.hermes/config.yaml`의 Hermes native MCP 설정에 `mcp_servers.alexandria`가 등록되어야 한다.

`~/.hermes/alexandria-hermes/mcp-config.json`만 생성되면 아직 끝난 것이 아니다.
이 파일은 snippet이고, 실제 runtime tool 노출은 `~/.hermes/config.yaml`의 `mcp_servers`가 담당한다.

### 0-1-a. `policy.yaml` contract

`alexandria-hermes hermes onboard`는 아래 위치에 usage policy를 설치한다.

```text
~/.hermes/alexandria-hermes/policy.yaml
```

기본 contract는 **ON**이다.

```yaml
enabled: true
mode: local_first_library_when_needed

read:
  search_library: true
  recall_context: true
  get_skill: true
  get_prompt: true

write:
  auto_capture_context: true
  auto_submit_skill_candidates: true
  auto_capture_prompt_candidates: true
  default_state: DRAFT
  allow_active_without_review: false

self_acquisition:
  enabled: true
  hermes_can_research_directly: true
  self_acquisition_enabled: true

librarian:
  enabled: true
  optional: true
  hermes_self_acquisition_fallback: true
  delegate_when_busy: false
  delegate_when_self_acquisition_cost_high: false
  require_explicit_user_request_for_librarian: true

safety:
  secret_lint_required: true
  reject_raw_secrets: true
  redact_before_store: true
  store_full_conversation: false
  store_temporary_todos: false

user_interruption:
  ask_before_routine_curation: false
  report_saved_assets_in_final_summary: true
```

해석 규칙:

- `enabled: true`면 Hermes는 먼저 현재 대화, local memory, loaded/local skill을 사용하고, 그 정보가 부족하거나 이전 작업/공유 장기기억이 필요할 때 Alexandria를 사용한다.
- `enabled: false`면 Hermes는 status/diagnostics 또는 사용자의 명시 요청 외에는 Alexandria tool/CLI를 사용하지 않는다.
- `START_HERE`는 unfamiliar agent가 로컬 맥락이 부족할 때 보는 도서관 입구이지, 모든 작업의 mandatory first call이 아니다.
- 사서는 optional이며 기본값은 명시 요청 필요다. 사서 provider/profile이 없거나 사용자가 요청하지 않았어도 Hermes는 직접 조사하고 skill/prompt/context candidate를 DRAFT/PENDING_REVIEW로 제출할 수 있어야 한다.
- 전체 off는 CLI policy로 관리하고, “이번 작업에서만 쓰지 마” 같은 지시는 현재 세션/task 한정 instruction으로 처리한다.

CLI toggle:

```bash
alexandria-hermes --json hermes policy status --hermes-home "$HERMES_HOME"
alexandria-hermes --json hermes policy disable --hermes-home "$HERMES_HOME"
alexandria-hermes --json hermes policy enable --hermes-home "$HERMES_HOME"
```

### 0-2. 처음 설치 직후 실행할 명령

repo root에서 실행한다.

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
export ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-${SERVICE_OPERATOR_API_KEY:-}}"

# backend dependency / DB migration
cd backend
uv sync
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/alexandria_hermes.db}" uv run alembic upgrade head
cd ..

# backend가 아직 안 떠 있다면 별도 터미널에서 실행한다.
# 예: docker compose up backend frontend
# 또는 프로젝트의 로컬 실행 절차에 맞춰 backend를 띄운다.

# CLI / backend health 확인
alexandria-hermes --base-url "$ALEXANDRIA_API_URL" --json health

# Hermes integration asset 설치
alexandria-hermes --json hermes onboard \
  --hermes-home "$HERMES_HOME" \
  --api-url "$ALEXANDRIA_API_URL" \
  --operator-api-key "${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --install-prompts \
  --install-mcp

# Hermes native MCP 등록
ALEXANDRIA_CLI="$(command -v alexandria-hermes)"
hermes mcp add alexandria \
  --command "$ALEXANDRIA_CLI" \
  --args mcp serve \
  --env ALEXANDRIA_API_URL="$ALEXANDRIA_API_URL" \
  --env ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --env HERMES_HOME="$HERMES_HOME"

# 연결 검증
hermes mcp test alexandria
```

설정 후에는 Hermes CLI/Gateway/Discord 세션을 새로 시작한다. MCP tool discovery는 세션 시작 시점에 일어난다.

### 0-3. 선택 사항: 설치 후 인지 확인 프롬프트

설치와 재시작이 끝나면 policy 기본값이 ON이라 Hermes는 별도 주문 없이도 Alexandria를 사용할 수 있지만, **먼저 로컬/현재 컨텍스트와 local skill을 확인하고 부족할 때만** Alexandria를 써야 한다.
아래 프롬프트는 필수 설정이 아니라 “새 agent가 사용자를 다시 코칭시키지 않고 local-first / Alexandria-when-needed 계약을 따르는지” 확인하는 용도다.

```text
Alexandria-Hermes가 설치되어 있습니다. 새 Hermes/agent는 먼저 로컬/현재 컨텍스트, Hermes local memory, loaded/local skills를 확인합니다. 그것으로 충분하면 Alexandria를 호출하지 않고 바로 작업합니다.

로컬 정보가 부족하거나 이전 작업을 이어가거나 durable/shared project memory가 필요하면 `~/.hermes/alexandria-hermes/policy.yaml`을 확인하고, policy가 enabled일 때 `START_HERE`, project-state, decision/handoff/bug-root-cause, relevant skill/prompt context를 recall/search한 뒤 작업합니다.

- 사용자가 매번 “Alexandria를 사용해”라고 말해야 하는 구조가 아닙니다.
- 그렇다고 매번 Alexandria부터 호출하는 구조도 아닙니다. local-first, Alexandria-when-needed입니다.
- policy가 `enabled: false`이면 status/diagnostics 또는 제가 명시 요청한 경우 외에는 Alexandria를 사용하지 마세요.
- 필요한 skill/prompt가 local Hermes에 없거나 약하면 Alexandria에서 검색하세요.
- Alexandria에도 없으면 사서가 없어도 직접 조사해서 reusable skill/prompt/context candidate를 DRAFT/PENDING_REVIEW로 제출하세요.
- 사서는 optional 협업자이며 기본적으로 명시 요청이 있을 때만 사용하세요.
- raw secret/operator key/provider token/전체 대화 로그/단순 진행상황은 저장하지 마세요.
- 사용한 핵심 context만 간단히 보고하고 내부 reasoning은 노출하지 마세요.
```

### 0-3-a. 기능 smoke test: capture → recall

서버와 CLI가 붙은 뒤에는 설치 성공을 health만으로 판단하지 말고, 최소 한 번 Context Vault 기능을 확인한다.

```bash
cat > /tmp/alexandria-first-context.md <<'MD'
# First Alexandria context

Alexandria-Hermes is installed locally and should preserve durable agent context.
MD

alexandria-hermes --base-url "$ALEXANDRIA_API_URL" context save \
  --title "First Alexandria context" \
  --kind DECISION \
  --project alexandria-hermes \
  --content-file /tmp/alexandria-first-context.md

alexandria-hermes --base-url "$ALEXANDRIA_API_URL" context recall \
  "durable agent context" \
  --strategy FTS_ONLY \
  --project alexandria-hermes \
  --limit 3
```

성공 기준: recall 결과에 방금 저장한 context가 포함되고, UI의 `/contexts` 또는 `/rag-inspector`에서 확인할 수 있다.

### 0-4. “바로 사용 가능” 성공 기준

처음 설치가 제대로 끝나면 아래가 모두 성립해야 한다.

- `alexandria-hermes --json health`가 `{"status":"ok"}`를 반환한다.
- `alexandria-hermes hermes doctor ...`에서 `skill_installed`, `mcp_config_installed`, `policy_installed`가 true다.
- `alexandria-hermes hermes policy status ...`가 `enabled: true`를 반환한다.
- `hermes mcp test alexandria`가 `Connected`와 tools discovered를 보여준다.
- 새 Hermes 세션에서 `mcp_alexandria_alexandria_search`, `mcp_alexandria_alexandria_recall_context`, `mcp_alexandria_alexandria_submit_skill_candidate` 같은 tool이 보인다.
- `~/.hermes/alexandria-hermes/prompts/alexandria-operating-loop.md`가 존재한다.

---

## 1. Hermes에게 전달할 설치/적용 프롬프트

아래 블록을 Hermes에게 그대로 전달한다.

````text
너는 지금부터 Alexandria-Hermes를 Hermes runtime에 설치/적용해야 합니다.

목표:
- Alexandria-Hermes backend를 CLI로 확인한다.
- Hermes home에 Alexandria-Hermes prompt/skill/MCP snippet을 설치한다.
- Hermes native MCP config에 Alexandria MCP 서버를 등록한다.
- Hermes가 다음 세션부터 Alexandria MCP tools를 직접 사용할 수 있게 만든다.
- `~/.hermes/alexandria-hermes/policy.yaml`을 default ON, local-first / Alexandria-when-needed usage contract로 설치하고 CLI on/off가 동작하는지 확인한다.
- 사서는 optional이다. provider/profile이 없거나 사용자가 명시적으로 요청하지 않았으면 Hermes self-acquisition으로 계속 가능해야 한다.

금지/주의:
- 사용자가 명시적으로 금지하거나 policy가 `enabled: false`이면 Alexandria search/recall/write/librarian tool을 호출하지 않는다.
- 사서가 필수라고 가정하지 않는다. librarian/provider delegation은 사용자가 명시 요청한 품질 보조/위임 경로일 뿐이다.
- npm supply-chain hold가 걸린 환경에서는 `npm install`, `npm uninstall`, `npx`를 실행하지 않는다.
- 기존 `~/.hermes/config.yaml`을 수정하기 전에는 timestamp backup을 만든다.
- repo의 unrelated 변경사항을 건드리지 않는다.

전제:
- Alexandria-Hermes backend는 사용자가 Docker Compose 또는 로컬 backend로 실행 중이거나 곧 실행한다.
- backend URL은 기본적으로 `http://localhost:8000` 이다.
- repo root는 사용자가 실행 중인 Alexandria-Hermes 프로젝트 디렉터리다.

0단계. 변수와 CLI 경로를 확정

```bash
export ALEXANDRIA_API_URL="${ALEXANDRIA_API_URL:-http://localhost:8000}"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

if command -v alexandria-hermes >/dev/null 2>&1; then
  export ALEXANDRIA_CLI="$(command -v alexandria-hermes)"
elif [ -x ./bin/alexandria-hermes ]; then
  export ALEXANDRIA_CLI="$(pwd)/bin/alexandria-hermes"
else
  echo "alexandria-hermes CLI를 찾을 수 없습니다. repo root에서 실행 중인지 확인하세요." >&2
  exit 1
fi

printf 'ALEXANDRIA_CLI=%s\nALEXANDRIA_API_URL=%s\nHERMES_HOME=%s\n' \
  "$ALEXANDRIA_CLI" "$ALEXANDRIA_API_URL" "$HERMES_HOME"
```

1단계. backend 연결 확인

```bash
"$ALEXANDRIA_CLI" --base-url "$ALEXANDRIA_API_URL" --json health
```

성공 기준:

```json
{"status":"ok"}
```

2단계. Hermes home과 Hermes config 경로 확인

```bash
mkdir -p "$HERMES_HOME"
hermes config path
hermes mcp list || true
```

`hermes config path`가 실패하면 Hermes CLI가 설치/초기화되어 있는지 먼저 확인한다.

3단계. Alexandria-Hermes assets 설치 dry-run

실제 쓰기 전에 planned files를 확인한다.

```bash
"$ALEXANDRIA_CLI" --json hermes onboard \
  --hermes-home "$HERMES_HOME" \
  --api-url "$ALEXANDRIA_API_URL" \
  --operator-api-key "${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --install-prompts \
  --install-mcp \
  --dry-run
```

planned files에 최소한 아래가 있어야 한다.

- `alexandria-hermes/policy.yaml`
- `skills/alexandria-hermes/alexandria-library/SKILL.md`
- `alexandria-hermes/alexandria-rules.md`
- `alexandria-hermes/prompts/use-alexandria-library.md`
- `alexandria-hermes/prompts/request-skill-acquisition.md`
- `alexandria-hermes/prompts/submit-skill-candidate.md`
- `alexandria-hermes/prompts/alexandria-operating-loop.md`
- `alexandria-hermes/mcp-config.json`

4단계. 실제 설치

Dry-run이 괜찮으면 실제 적용한다.

```bash
"$ALEXANDRIA_CLI" --json hermes onboard \
  --hermes-home "$HERMES_HOME" \
  --api-url "$ALEXANDRIA_API_URL" \
  --operator-api-key "${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --install-prompts \
  --install-mcp
```

기존 파일 때문에 skipped가 나오면, 내용을 확인한 뒤 필요할 때만 overwrite한다.
특히 `policy.yaml`이 skipped되면 기존 사용자 on/off 선택을 보존했다는 뜻이다.

정책 상태를 확인한다.

```bash
"$ALEXANDRIA_CLI" --json hermes policy status --hermes-home "$HERMES_HOME"
```

끄거나 다시 켜야 하면 아래를 사용한다.

```bash
"$ALEXANDRIA_CLI" --json hermes policy disable --hermes-home "$HERMES_HOME"
"$ALEXANDRIA_CLI" --json hermes policy enable --hermes-home "$HERMES_HOME"
```

필요하면 overwrite로 다시 적용한다. overwrite는 기존 policy 선택도 덮어쓰므로 주의한다.

```bash
"$ALEXANDRIA_CLI" --json hermes onboard \
  --hermes-home "$HERMES_HOME" \
  --api-url "$ALEXANDRIA_API_URL" \
  --operator-api-key "${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --install-prompts \
  --install-mcp \
  --overwrite
```

5단계. Alexandria-Hermes 설치 산출물 확인

```bash
"$ALEXANDRIA_CLI" --json hermes doctor \
  --hermes-home "$HERMES_HOME" \
  --api-url "$ALEXANDRIA_API_URL" \
  --operator-api-key "${ALEXANDRIA_OPERATOR_API_KEY:-}"
```

다음 값이 true여야 한다.

- `exists`
- `is_dir`
- `alexandria_dir`
- `skill_installed`
- `mcp_config_installed`
- `policy_installed`

생성된 MCP snippet도 확인한다.

```bash
MCP_CONFIG_PATH="$HERMES_HOME/alexandria-hermes/mcp-config.json"
python3 - "$MCP_CONFIG_PATH" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
print(path)
print(json.dumps(json.loads(path.read_text()), ensure_ascii=False, indent=2))
PY
```

6단계. Hermes native MCP config에 Alexandria 서버 등록

중요: 위 snippet은 참고용이다. Hermes Agent가 실제로 MCP tool을 노출하려면
`hermes mcp add` 또는 `~/.hermes/config.yaml` 편집을 통해 `mcp_servers`에 등록해야 한다.

먼저 config backup을 만든다.

```bash
HERMES_CONFIG_PATH="$(hermes config path)"
cp "$HERMES_CONFIG_PATH" "$HERMES_CONFIG_PATH.alexandria.$(date +%Y%m%d%H%M%S).bak"
```

선호 방법: Hermes CLI로 등록한다.

```bash
hermes mcp add alexandria \
  --command "$ALEXANDRIA_CLI" \
  --args mcp serve \
  --env ALEXANDRIA_API_URL="$ALEXANDRIA_API_URL" \
  --env ALEXANDRIA_OPERATOR_API_KEY="${ALEXANDRIA_OPERATOR_API_KEY:-}" \
  --env HERMES_HOME="$HERMES_HOME"
```

이미 `alexandria` 서버가 등록되어 있거나 CLI 등록이 원하는 형태로 동작하지 않으면,
`hermes config edit`으로 아래 구조가 `~/.hermes/config.yaml`에 있는지 확인/수정한다.

```yaml
mcp_servers:
  alexandria:
    command: "/absolute/path/to/alexandria-hermes"
    args:
      - "mcp"
      - "serve"
    env:
      ALEXANDRIA_API_URL: "http://localhost:8000"
      ALEXANDRIA_OPERATOR_API_KEY: "${ALEXANDRIA_OPERATOR_API_KEY:-}"
      HERMES_HOME: "/absolute/path/to/.hermes"
```

주의:

- `command`는 가능하면 `command -v alexandria-hermes`로 얻은 absolute path를 사용한다.
- `ALEXANDRIA_API_URL`은 Hermes/Gateway 프로세스가 접근 가능한 URL이어야 한다.
- 사서/provider OAuth tool을 쓰려면 `ALEXANDRIA_OPERATOR_API_KEY`가 backend의
  `SERVICE_OPERATOR_API_KEY`와 같아야 한다.
- basic local data-plane 테스트는 operator key 없이도 가능하지만, settings/provider/librarian delegation tool은 `ALEXANDRIA_OPERATOR_API_KEY`가 필요하다.
- `mcpServers`가 아니라 Hermes native config의 `mcp_servers`에 들어가야 한다.

7단계. Hermes MCP 연결 검증

```bash
hermes mcp list
hermes mcp test alexandria
```

성공 기준:

- `alexandria`가 enabled 상태다.
- `✓ Connected`가 나온다.
- tools discovered가 0보다 크다. 현재 기대 tool 예시는 다음과 같다.
  - `alexandria_search`
  - `alexandria_get_skill`
  - `alexandria_get_prompt`
  - `alexandria_recall_context`
  - `alexandria_rag_context`
  - `alexandria_capture_context`
  - `alexandria_submit_skill_candidate`
  - `alexandria_rag_status`

8단계. Hermes/Gateway 재시작 또는 새 세션 시작

MCP tool discovery는 Hermes 시작 시점에 일어난다. config를 바꾼 직후 현재 대화에 tool이 안 보이는 것은 정상이다.

CLI 세션이면 새 세션을 시작한다.

```bash
hermes chat -q "Alexandria MCP tools가 보이는지 확인해줘. 먼저 rag status만 읽어."
```

Gateway/Discord 세션이면 다음 중 하나를 수행한다.

```bash
hermes gateway restart
```

또는 Discord에서:

```text
/restart
/reset
```

9단계. Hermes runtime에서 실제 사용 정책

새 세션에서 Alexandria MCP tools는 Hermes tool registry에 보통 다음 이름으로 노출된다.

- `mcp_alexandria_alexandria_search`
- `mcp_alexandria_alexandria_get_skill`
- `mcp_alexandria_alexandria_get_prompt`
- `mcp_alexandria_alexandria_recall_context`
- `mcp_alexandria_alexandria_rag_status`
- `mcp_alexandria_alexandria_submit_skill_candidate`

운영 정책:

0. 먼저 `~/.hermes/alexandria-hermes/policy.yaml`을 usage contract로 취급한다.
   - `enabled: true`: local/current context를 먼저 쓰고, 부족하거나 이전 작업/장기기억이 필요할 때 Alexandria를 사용한다.
   - `enabled: false`: status/diagnostics 또는 명시 요청 외에는 Alexandria를 사용하지 않는다.
   - 전체 on/off는 `alexandria-hermes hermes policy enable|disable`로 관리한다.
1. 현재 대화, Hermes local memory, loaded/local/built-in skill을 먼저 확인한다.
2. 그 정보가 충분하면 Alexandria를 호출하지 않고 작업한다.
3. 로컬 정보가 부족하거나 `이어서/전에/지난번/기억`, START_HERE, project-state, decision, handoff, bug root cause, prompt/skill discovery, durable context 저장 신호가 있으면 Alexandria에서 `alexandria_search` 또는 `alexandria_recall_context`를 사용한다.
4. 적절한 항목이 없으면 Hermes가 직접 조사해 reusable skill candidate를 작성한다.
5. `alexandria_submit_skill_candidate`로 candidate를 제출한다.
6. evidence URL과 source summary를 반드시 포함한다.
7. candidate id와 harness status를 보고한다.
8. librarian은 optional 협업자이며 기본적으로 명시 요청이 있을 때만 사용한다. 없어도 Hermes self-acquisition을 중단하지 않는다.

10단계. 최종 보고 형식

설치 완료 후 사용자에게 아래 형식으로 보고한다.

- backend health:
- hermes_home:
- alexandria_cli:
- dry-run planned files:
- written/skipped files:
- doctor 결과:
- policy status:
- MCP snippet 위치:
- Hermes native MCP 등록 방식:
- `hermes mcp test alexandria` 결과:
- Gateway/세션 재시작 필요 여부:
- 다음 테스트 준비 여부:
````

---

## 2. 설치 후 Hermes에게 전달할 self-acquisition 테스트 프롬프트

설치가 끝나고 Hermes/Gateway를 재시작한 뒤 아래 블록을 Hermes에게 전달한다.

```text
이제 사서 없이 Alexandria-Hermes self-acquisition 테스트를 진행하세요.

주제:
pytest fixture cleanup strategy

절차:
1. 이번 테스트에서는 local skill이 없다고 가정하세요.
2. 먼저 Alexandria MCP tool로 RAG 상태를 확인하세요.
   - 예상 tool: `mcp_alexandria_alexandria_rag_status`
3. Alexandria에서 관련 skill/prompt/context를 검색하세요.
   - 예상 tool: `mcp_alexandria_alexandria_search`
   - query: `pytest fixture cleanup strategy`
   - limit: 2
   - strategy: `FTS_ONLY`
4. 적절한 항목이 없으면 직접 reusable skill candidate를 작성하세요.
5. evidence_urls 최소 1개와 source_summary를 포함하세요.
6. `mcp_alexandria_alexandria_submit_skill_candidate`로 제출하세요.
7. candidate id와 details.harness.status를 알려주세요.
8. `alexandria_ask_librarian` 또는 librarian OAuth/job tool은 호출하지 마세요.

최종 답변:
- RAG status:
- 검색 결과 요약:
- self-acquisition 수행 여부:
- candidate id:
- harness status:
- evidence URLs:
- UI 확인 위치:
```

---

## 3. 기대 결과

Hermes가 정상적으로 설치/적용되면 다음이 가능해야 한다.

1. Hermes가 Alexandria-Hermes MCP server를 인식한다.
2. `~/.hermes/alexandria-hermes/policy.yaml`이 존재하고 기본값은 `enabled: true`, `mode: local_first_library_when_needed`다.
3. `alexandria-hermes hermes policy enable|disable|status`로 사람이 Hermes 사용 여부를 전역 on/off 할 수 있다.
4. `hermes mcp test alexandria`가 연결과 tool discovery를 통과한다.
5. 새 Hermes 세션에서 Alexandria MCP tools가 `mcp_alexandria_*` 형태로 노출된다.
6. Hermes가 현재 대화/local memory/local skill로 충분한 작업은 Alexandria 없이 처리한다.
7. Hermes가 로컬 정보가 부족하거나 이전 작업/장기기억이 필요할 때 사서 없이 `alexandria_search` / `alexandria_recall_context`를 사용할 수 있다.
8. Hermes가 직접 조사한 skill candidate를 `alexandria_submit_skill_candidate`로 제출할 수 있다.
9. 제출된 candidate details에 아래 정보가 저장된다.
   - `acquisition_method: SELF_ACQUISITION`
   - `evidence_urls`
   - `source_summary`
   - `harness.status`
10. UI에서는 아래 위치에서 확인한다.

```text
Library -> candidate skill detail -> Self-acquisition evidence
```

---

## 4. ChatGPT/Codex OAuth provider를 추가로 연결할 때

Hermes upstream은 Codex OAuth를 provider 기본값으로 처리한다. Alexandria-Hermes도 같은 방향으로 맞춘다.

절차:

1. repo root `.env`에는 operator key만 있으면 된다. Codex OAuth public
   metadata는 Hermes처럼 backend 코드 기본값으로 제공된다.

   ```bash
   SERVICE_OPERATOR_API_KEY=<generate-a-local-operator-key>
   ```

   특별한 배포에서만 `SERVICE_CODEX_OAUTH_*`를 local override로 설정한다.
   access token / refresh token은 `.env`에 두지 않는다.

2. backend와 frontend를 실행한다.
3. 브라우저에서 `http://localhost:3000/settings/librarians`를 연다.
4. `ChatGPT / Codex OAuth` 카드를 선택한다.
5. 이름은 기본값을 그대로 두고 `ChatGPT/Codex OAuth 시작`을 누른다.
6. 브라우저 승인 화면에서 표시된 user code로 승인한다.
7. UI가 자동으로 승인 상태를 확인한다.

주의:

- 일반 사용자는 `device_authorization_url`, `token_url`, `client_id`를 입력하지 않는다.
- token 원문은 브라우저 state에 저장하지 않고 backend provider secret 저장소에만 보관한다.
- advanced endpoint override는 OpenAI 허용 endpoint를 검증하기 위한 예외 경로다.

---

## 5. 실패 시 확인할 것

### backend health 실패

- backend가 실행 중인지 확인한다.
- Docker Compose라면 backend port `8000`이 host로 노출되어 있는지 확인한다.
- CLI base URL을 명시한다.

```bash
"$ALEXANDRIA_CLI" --base-url "$ALEXANDRIA_API_URL" --json health
```

### CLI 실행 실패

- backend 가상환경이 준비되어 있는지 확인한다.

```bash
cd backend
uv sync
cd ..
./bin/alexandria-hermes --base-url http://localhost:8000 --json health
```

### symlink된 CLI wrapper가 잘못된 repo root를 계산함

`~/.local/bin/alexandria-hermes`가 symlink이고 wrapper가 symlink 위치 기준으로 repo root를 계산하면,
`~/.local/backend`를 찾으려 하며 실패할 수 있다.

증상 예시:

```text
alexandria-hermes: backend virtualenv not found. Run: cd /Users/.../.local/backend && uv sync
```

해결:

```bash
cat > ~/.local/bin/alexandria-hermes <<'SH'
#!/usr/bin/env sh
set -eu
exec "/ABSOLUTE/PATH/TO/alexandria-hermes/bin/alexandria-hermes" "$@"
SH
chmod +x ~/.local/bin/alexandria-hermes
command -v alexandria-hermes
alexandria-hermes --base-url http://localhost:8000 --json health
```

### MCP snippet은 있는데 Hermes에서 tool이 보이지 않음

- `~/.hermes/alexandria-hermes/mcp-config.json`만 있으면 부족하다.
- Hermes native config인 `~/.hermes/config.yaml`에 `mcp_servers.alexandria`가 있어야 한다.

확인:

```bash
hermes config path
hermes mcp list
hermes mcp test alexandria
```

### `hermes mcp test alexandria`는 성공하지만 현재 Discord 대화에서 tool이 안 보임

- 현재 세션은 시작 시점의 tool 목록을 유지한다.
- Gateway 또는 세션을 재시작한다.

```bash
hermes gateway restart
```

또는 Discord에서:

```text
/restart
/reset
```

### RAG status가 vector disabled / embedding degraded로 보임

현재 기본 설정은 local FastEmbed + sqlite-vec vector retrieval을 켠다. 정상 상태는
아래처럼 `HYBRID`가 기본 전략으로 보여야 한다.

```json
{
  "fts": "HEALTHY",
  "vector": "HEALTHY",
  "embedding": "HEALTHY",
  "default_strategy": "HYBRID"
}
```

아래 상태가 보이면 vector 설정이 꺼졌거나 embedding provider가 주입되지 않은
것이다.

```json
{
  "fts": "HEALTHY",
  "vector": "DISABLED",
  "embedding": "DEGRADED",
  "default_strategy": "FTS_ONLY"
}
```

이 경우 SQLite FTS 검색은 정상이고 vector recall만 비활성화된 상태다.
`SERVICE_RAG_VECTOR_ENABLED=true`,
`SERVICE_RAG_EMBEDDING_PROVIDER=fastembed`,
`SERVICE_RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
설정을 확인한 뒤 backend를 재시작한다. 기존 DB는 `uv run alembic upgrade head`
로 embedding 컬럼 migration을 적용해야 한다.

### self-acquisition 제출은 됐지만 harness가 `NEEDS_REVIEW`

대개 아래 중 하나가 누락된 것이다.

- title
- purpose
- content
- evidence URL
- source summary

근거 URL을 최소 1개 넣고 다시 제출한다.

### librarian tool이 노출되어 있음

MCP discovery 결과에 `alexandria_ask_librarian`, `alexandria_librarian_oauth_*`,
`alexandria_librarian_job_status`가 보이는 것은 정상이다.
다만 이번 테스트에서는 사용자가 명시적으로 요청하지 않는 한 호출하지 않는다.
