# Pydantic and Validation Rules

## 사용 대상

Pydantic v2는 검증과 직렬화가 필요한 경계에 사용한다.

- FastAPI Request와 Response
- MCP Input과 Output
- JSON 또는 YAML에서 읽은 안정된 Contract
- Obsidian Canonical Frontmatter
- Search Request와 Result
- Lifecycle Command와 Result
- Librarian Draft와 Proposal
- Audit와 Run Report

## 사용하지 않는 대상

다음에 기계적으로 사용하지 않는다.

- SQLAlchemy ORM Entity
- 검증 완료 후 내부 계층 간 전달 DTO
- 단순한 지역 계산 값
- 성능상 중요한 Row Processing
- Pydantic 전환의 실익이 없는 기존 내부 객체

## ConfigDict

안정된 Named-field Boundary Contract의 권장 기본:

```python
ConfigDict(
    extra="forbid",
    frozen=True,
    validate_default=True,
)
```

모든 Schema에 동일 Config를 복사하지 않는다. 공통 Base를 도입할 경우 실제 저장소의 호환성을 먼저 확인한다.

다음 옵션은 전역 기본이 아니다.

- `strict=True`
- `use_enum_values=True`
- `validate_assignment=True`
- `str_strip_whitespace=True`
- `populate_by_name=True`
- `arbitrary_types_allowed=True`
- `from_attributes=True`

## Raw Validation

외부 또는 신뢰할 수 없는 값:

```python
request = ContextCreateRequest.model_validate(raw_payload)
frontmatter = ContextFrontmatter.model_validate(raw_frontmatter)
```

JSON 문자열 또는 Byte:

```python
event = EventSchema.model_validate_json(raw_json)
```

## Internal Construction

이미 타입이 확인된 내부 값:

```python
result = ContextCreateResult(
    context_id=context_id,
    status=status,
)
```

같은 함수에서 만든 Dictionary Literal을 `model_validate`로 감싸 내부 Constructor처럼 사용하지 않는다.

## RootModel

Payload 전체가 Root Value일 때만 사용한다.

- 의미 있는 ID Collection
- 중복 금지 Collection
- Collection 자체가 Invariant를 소유하는 경우

일반 Named-field Contract에는 BaseModel을 사용한다.

## Enum

Scope, Lifecycle, Error Code처럼 공유되는 Symbolic Set은 Enum을 사용한다.

작은 Contract 한 곳에서만 쓰는 값은 Literal을 사용할 수 있다.

`use_enum_values=True`를 전역 적용하지 않는다. 내부 로직에서 Enum 의미가 필요한지 먼저 확인한다.

## Default

Default는 Protocol 또는 Domain에 실제 기본값이 있을 때만 둔다.

Construction 편의를 위해 Required Field를 Default로 완화하지 않는다.

## Nullability

`T | None`은 None이 실제 유효 상태일 때만 사용한다.

누락, 미정, 빈 문자열, None을 같은 의미로 취급하지 않는다.
