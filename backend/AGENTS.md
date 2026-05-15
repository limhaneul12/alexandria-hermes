# Backend AGENTS.md

## Scope
이 문서는 `backend/` 디렉터리와 그 하위 전체에 적용됩니다.

## Mandatory rule sources
backend 코드를 수정하기 전에는 아래 rule 문서를 먼저 확인하고, 현재 backend 개발 규칙의 source of truth로 취급합니다.

### Architecture rules

```text
backend/.agents/rule/archtecture_rule/00-path-conventions.md
backend/.agents/rule/archtecture_rule/01-boundaries-and-layout.md
backend/.agents/rule/archtecture_rule/02-shared-runtime-bootstrap.md
backend/.agents/rule/archtecture_rule/03-testing-and-quality-gates.md
backend/.agents/rule/archtecture_rule/04-generation-and-scaffolding.md
backend/.agents/rule/archtecture_rule/05-type-and-schema-rules.md
backend/.agents/rule/archtecture_rule/06-adoption-plan.md
backend/.agents/rule/archtecture_rule/07-di-and-wiring-rule.md
backend/.agents/rule/archtecture_rule/08-exception-and-error-handling-rule.md
backend/.agents/rule/archtecture_rule/09-implementation-boundary-rule.md
```

### Test rules

```text
backend/.agents/rule/test_rule/00-source-of-truth.md
backend/.agents/rule/test_rule/01-location-and-discovery.md
backend/.agents/rule/test_rule/02-philosophy-and-style.md
backend/.agents/rule/test_rule/03-tdd-and-quality-gates.md
backend/.agents/rule/test_rule/04-red-flags-and-reporting.md
```

### Type / enum rules

```text
backend/.agents/rule/type_enum_rule/type-development-rules.md
backend/.agents/rule/type_enum_rule/pydantic/04-enums-literals-and-shared-types.md
```

### Pydantic / schema boundary rules

```text
backend/.agents/rule/pydantic_rule/README.md
backend/.agents/rule/pydantic_rule/01-configdict-and-model-shape.md
backend/.agents/rule/pydantic_rule/02-strictness-defaults-and-nullability.md
backend/.agents/rule/pydantic_rule/03-boundary-normalization.md
backend/.agents/rule/pydantic_rule/schema-boundary-rules.md
```

### Folder / module cohesion rules

```text
backend/.agents/rule/layout_rule/naming-and-folder-rules.md
backend/.agents/rule/layout_rule/module-cohesion-rules.md
```

## Rules

- backend 구조, 계층, DI, 예외, 테스트, 타입/enum, Pydantic/schema boundary, folder/module cohesion 정책은 위 문서를 기준으로 따릅니다.
- 내부 object DTO는 dataclass, 외부 I/O DTO는 Pydantic v2 schema, dictionary payload contract는 TypedDict를 기본값으로 사용합니다.
- 새로운 backend 패턴을 도입하기 전에 위 규칙과 충돌하지 않는지 먼저 확인합니다.
- 규칙과 실제 구현이 어긋나면 임의로 우회하지 말고, 규칙 문서와 구현 중 무엇이 source of truth인지 먼저 정리합니다.
- 상위 시스템/개발자/사용자 지시가 있으면 그 지시가 우선합니다.
