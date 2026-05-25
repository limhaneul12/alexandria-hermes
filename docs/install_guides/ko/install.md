# Alexandria-Hermes 설치

프론트엔드 런타임은 제거되었습니다. 이제 backend/CLI/MCP 서비스와 Obsidian Markdown vault를 연결합니다.

## 자동 생성 vault로 설치

터미널 1:

```bash
cd backend
uv sync
uv run alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
uv run alexandria-hermes serve \
  --env-file "$HOME/.hermes/alexandria-hermes/.env" \
  --host 127.0.0.1 \
  --port 8000
```

터미널 2, backend가 켜진 뒤:

```bash
cd backend
uv run alexandria-hermes obsidian init
uv run alexandria-hermes obsidian reindex
```

Obsidian에서 다음 vault를 엽니다.

```text
~/.hermes/alexandria-hermes/data/obsidian-vault
```

## 이미 만든 `Alexandria` vault에 붙이기

Obsidian에서 이미 `~/Desktop/Alexandria` vault를 만들었다면 이렇게 설정합니다.

```bash
cd backend
uv sync
uv run alexandria-hermes setup \
  --mode backend-daemon \
  --apply \
  --write-guidebook \
  --obsidian-vault-path "$HOME/Desktop/Alexandria" \
  --alexandria-obsidian-root "."
```

`--alexandria-obsidian-root "."`는 vault 자체를 Alexandria 작업공간으로 쓰겠다는 뜻입니다. 그래서 `Alexandria/Alexandria` 중첩 폴더가 생기지 않습니다.

실제 로컬 smoke test는 `/Users/imhaneul/Desktop/Alexandria` + root `.`로 진행했습니다. reindex는 Markdown 5개를 보고 Alexandria frontmatter가 있는 4개를 색인했고, Obsidian 기본 환영 노트 1개는 건너뛰었습니다.

## Obsidian 설치와 사서 side pane 연결

```bash
brew install --cask obsidian
REPO_ROOT="$(git rev-parse --show-toplevel)"
VAULT="$HOME/Desktop/Alexandria"
mkdir -p "$VAULT/.obsidian/plugins"
ln -s "$REPO_ROOT/integrations/obsidian/alexandria-librarian" \
  "$VAULT/.obsidian/plugins/alexandria-librarian"
```

Obsidian에서 Community plugins를 켜고 **Alexandria Librarian**을 활성화하세요. pane을 쓰기 전 backend는 켜져 있어야 합니다.

## Docker Compose

```bash
docker compose up --build
```

backend는 `http://127.0.0.1:8000`에서 실행됩니다.
