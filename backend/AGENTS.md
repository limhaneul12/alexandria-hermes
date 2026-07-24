# Backend AGENTS.md

## Scope

이 문서는 `backend/` 디렉터리와 그 하위 전체에 적용됩니다.

## Mandatory rule sources

Backend 코드를 수정하기 전에는 다음 문서를 순서대로 읽습니다.

1. `backend/.agents/docs/rule/규칙.md`
2. `backend/.agents/docs/rule/README.md`
3. `README.md`에서 현재 작업과 직접 관련된 세부 규칙
4. 사용자가 명시적으로 지정한 PRD 또는 작업 문서
5. 관련 코드와 테스트

Backend 개발 규칙의 Source of Truth는 다음 디렉터리입니다.

```text
backend/.agents/docs/rule/
```

PRD, 회의록, 기능 요구사항은 개발 규칙이 아닙니다. 사용자가 명시적으로 지정하거나 저장소에서 현재 Task에 연결한 경우에만 작업 입력으로 사용합니다.

## Rules

- 기존 구조를 먼저 조사하고 재사용합니다.
- 내부 object DTO는 dataclass, 외부 I/O DTO는 Pydantic v2 schema, dictionary payload contract는 TypedDict를 기본값으로 사용합니다.
- Obsidian Markdown은 Canonical Storage이며 SQLite, FTS, Vector, Embedding, Graph는 재구축 가능한 Index 또는 Read Model입니다.
- 새로운 Backend 패턴을 도입하기 전에 규칙과 기존 구현의 충돌 여부를 확인합니다.
- 규칙과 실제 구현이 어긋나면 임의로 우회하지 않고 Source of Truth를 먼저 정리합니다.
- 상위 시스템, 개발자, 사용자 지시가 있으면 해당 지시가 우선합니다.
