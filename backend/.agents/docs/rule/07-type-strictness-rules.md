# Type Strictness Rules

## Production Type Policy

Production Code의 Public 함수, 메서드, Class Field에는 명시적 타입을 작성한다.

Return Type을 생략하지 않는다.

## Any

`Any`는 기본 금지다.

허용 가능한 경계:

- 타입 정보가 없는 Third-party Library
- Raw JSON 또는 YAML Parser의 최초 수신 지점
- Dynamic Plugin 또는 MCP Transport
- ORM 또는 Framework Hook의 피할 수 없는 경계

허용할 때 다음을 지킨다.

- 한 함수 또는 한 모듈의 Boundary에 국한한다.
- 즉시 TypedDict, Pydantic, Dataclass로 정규화한다.
- 왜 Any가 필요한지 짧게 설명한다.
- Core Service와 Repository Public Surface로 전달하지 않는다.

## object

`dict[str, object]`를 Any의 대체품처럼 사용하지 않는다.

실제 Shape가 알려져 있으면 명시적 Contract를 만든다.

## Optional

Optional은 값이 실제로 None일 수 있다는 의미다.

다음 이유로 Optional을 사용하지 않는다.

- Caller가 값을 넘기기 귀찮음
- 아직 설계를 결정하지 않음
- 오류를 피하고 싶음
- 빈 문자열과 None을 구분하지 않음
- Legacy Payload를 그대로 통과시킴

## Omission과 None

- Key가 없을 수 있음: `NotRequired`
- Key는 있으나 값이 None일 수 있음: `T | None`
- 둘 다 가능: `NotRequired[T | None]`

세 의미를 구분한다.

## Strict Types

`StrictStr`, `StrictInt`, `StrictBool`, Model-level `strict=True`는 전역 기본이 아니다.

Coercion이 실제 오류를 숨기는 Field에만 사용한다.

좋은 후보:

- Protocol Discriminator
- Lifecycle Status
- Scope
- Event Kind
- Machine-controlled Boolean
- Version Number

## Union

넓은 Union을 피한다.

`str | int | dict | list | None` 같은 광범위 Union은 Raw Boundary에만 제한한다.

Canonical Contract에서는 Discriminated Union, Enum, 명명된 Model을 사용한다.

## Literal과 Enum

- 한 Contract에 국한된 작은 값 집합: Literal
- 여러 Module이 공유하는 값 집합: Enum

Loose String으로 Protocol 값을 전달하지 않는다.

## cast

Cast는 타입 검사기를 속이는 수단이 아니다.

허용할 때:

- Runtime 검사 직후 Narrowing
- Library Typing 결함
- 불변식이 코드로 증명되는 경우

Cast 옆에서 근거를 알 수 있어야 한다.

## type: ignore

Broad Ignore를 금지한다.

필요하면 정확한 Error Code와 이유를 적는다.

기존 Checker 정책을 약화해 오류를 없애지 않는다.

## Keyword Arguments

동일 타입 인자가 여러 개이거나 순서가 바뀌기 쉬운 함수는 Keyword Argument를 사용한다.

## Collection

- 변경하지 않는 Sequence: `tuple[T, ...]`
- 실제 Mutation이 필요한 경우: `list[T]`
- 고유성 의미가 있는 경우: `set[T]` 또는 Root Contract
- 읽기 전용 Mapping: `Mapping[K, V]`
- 변경이 필요한 Mapping: `dict[K, V]`
