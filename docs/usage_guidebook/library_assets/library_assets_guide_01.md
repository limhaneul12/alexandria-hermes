# Library Assets Guide 01 — skills/prompts candidate search와 full load

## 목적

Alexandria-Hermes의 library asset 흐름을 이해한다.

핵심 원칙:

```text
검색은 thin candidate 중심
선택된 skill/prompt만 full load
사용 후 usage history 기록
```

즉 모든 skill/prompt 본문을 RAG chunk처럼 무조건 밀어 넣는 구조가 아니다.

## 언제 사용하나

- Hermes/local skill만으로 부족한 reusable 절차를 찾을 때
- prompt/skill 후보를 훑은 뒤 하나만 자세히 읽고 싶을 때
- agent가 선택한 asset 사용 이력을 남기고 싶을 때

## 후보 검색

```bash
alexandria-hermes library search "FastAPI dependency injection" \
  --type SKILL \
  --content-mode candidate \
  --limit 10
```

성공 기준:

- title/summary/tags/details 중심의 후보 목록을 받는다.
- full body를 전부 읽기 전에 후보를 좁힌다.

## 선택 항목 full load

```bash
alexandria-hermes --json skills get <skill-id>
alexandria-hermes --json prompts get <prompt-id>
```

## MCP/Hermes에서의 기대 흐름

```text
mcp_alexandria_alexandria_search
→ candidate 목록 확인
→ mcp_alexandria_alexandria_get_skill 또는 get_prompt
→ 필요한 경우 record_usage
```

## Self-acquisition fallback

검색 결과가 없으면 사서를 필수로 호출하지 않는다.

```text
Hermes가 직접 조사
→ reusable candidate 작성
→ evidence_urls/source_summary 포함
→ alexandria_submit_skill_candidate
→ DRAFT/PENDING_REVIEW로 저장
```

## 금지

- raw secret/API key/token을 skill/prompt/context에 저장하지 않는다.
- 전체 대화 로그를 asset으로 저장하지 않는다.
- evidence 없는 skill candidate를 OSS 예제로 홍보하지 않는다.
