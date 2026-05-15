# 00. Backend Test Rule Sources

## Goal

Backend 테스트 규칙의 source of truth를 명확히 유지한다.

## Source of truth

아래 문서를 backend 테스트 규칙의 근거 문서로 본다.

```text
AGENTS.md
backend/AGENTS.md
backend/.agents/rule/test_rule/01-location-and-discovery.md
backend/.agents/rule/test_rule/02-philosophy-and-style.md
backend/.agents/rule/test_rule/03-tdd-and-quality-gates.md
backend/.agents/rule/test_rule/04-red-flags-and-reporting.md
backend/pyproject.toml
backend/Makefile
```

## Rule

- backend 테스트 규칙이 애매하면 위 문서를 먼저 확인한다.
- 새로운 테스트 규칙을 추가할 때는 위 문서와 충돌하지 않는지 먼저 확인한다.
- 문서와 구현이 어긋나면 조용히 우회하지 말고 source of truth를 먼저 정리한다.
- 외부에 없는 정책 문서를 source of truth로 참조하지 않는다.
