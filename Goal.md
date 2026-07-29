Alexandria-Hermes를 실제 운영 환경에서 dogfooding한 결과, Context 저장·Frontmatter 정규화·민감정보 마스킹·검색 메타데이터 처리 과정에서 범용적인 데이터 무결성 문제가 발견되었습니다.

이번 작업의 목적은 Evidence Intelligence 전용 예외 처리를 추가하는 것이 아닙니다.

Evidence Intelligence 문서는 문제를 발견하게 된 실제 재현 사례일 뿐이며, Alexandria-Hermes에 저장되는 모든 Context, Memory, Note, Artifact 및 향후 확장되는 문서 유형에 공통으로 적용되는 저장 파이프라인 문제로 접근해야 합니다.

이전 세션의 분석이나 상태 결과를 그대로 신뢰하지 말고, 현재 저장소 코드와 실제 실행 결과를 기준으로 처음부터 조사하고 수정해 주세요.

---

# 1. Dogfooding 피드백

Alexandria-Hermes를 실제 장기기억 및 Evidence 문서 저장소로 사용하면서 다음 현상을 확인했습니다.

문서 파일은 정상적으로 생성되고 Vault 재색인도 성공합니다.

RAG 상태는 `HEALTHY`, Operational Readiness는 `READY`, 문서의 `index_status`는 `indexed`로 표시됩니다.

하지만 저장된 Frontmatter와 검색 동작을 실제로 점검하니 다음과 같은 문제가 발견되었습니다.

## 1.1 태그 직렬화 문제

호출 측에서는 여러 태그를 전달했지만, 실제 저장 결과에서는 태그 배열이 아니라 Python tuple 표현 전체가 하나의 문자열 태그로 저장되었습니다.

실제 사례:

```yaml
tags: "('Evidence Intelligence', 'Closing Review v3', 'Market', 'KRX', '2026-07-29')"
```

또는 API 응답에서 다음과 같이 나타납니다.

```text
[
  "('Evidence Intelligence', 'Closing Review v3', 'Market', 'KRX', '2026-07-29')"
]
```

정상 결과는 다음과 같아야 합니다.

```yaml
tags:
  - Evidence Intelligence
  - Closing Review v3
  - Market
  - KRX
  - "2026-07-29"
```

빈 태그가 다음처럼 저장된 사례도 있습니다.

```yaml
tags: "()"
```

정상 결과는 다음이어야 합니다.

```yaml
tags: []
```

이 문제로 인해 문서는 본문 검색과 RAG 검색에서는 발견되지만, 개별 태그를 이용한 필터 검색에서는 조회되지 않습니다.

예를 들어 다음 필터가 0건을 반환합니다.

```python
tags=["Evidence Intelligence", "2026-07-29"]
```

이것은 Evidence Intelligence에 한정된 문제가 아니라 Alexandria의 범용 Frontmatter 직렬화 또는 입력 정규화 문제로 판단됩니다.

---

## 1.2 Boolean 타입 손실

Boolean이어야 하는 값이 문자열로 저장됩니다.

실제 사례:

```yaml
source_of_truth: "true"
```

정상 결과:

```yaml
source_of_truth: true
```

현재 저장 결과가 단순히 사람이 읽을 때만 비슷해 보일 뿐, YAML 파싱 이후 타입은 서로 다릅니다.

향후 검색 필터, 정책 판정, 문서 상태 분기, lifecycle 처리에서 다음과 같은 코드가 사용되면 문제가 발생할 수 있습니다.

```python
if metadata.source_of_truth is True:
    ...
```

따라서 Alexandria가 Boolean으로 정의한 모든 메타데이터 필드는 저장과 조회의 round-trip 과정에서 Boolean 타입을 유지해야 합니다.

---

## 1.3 공개 URL의 과도한 민감정보 마스킹

일반 공개 기사 URL이 secret-like content로 감지되어 URL 전체가 다음과 같이 변경됩니다.

```text
https://<REDACTED_LONG_VALUE>
```

동시에 문서에는 다음 경고가 추가됩니다.

```yaml
redaction_warnings:
  - potential secret-like content was redacted
```

이로 인해 문서 본문과 Evidence 설명은 보존되지만 원문 출처로 다시 접근할 수 없습니다.

Alexandria를 Evidence 보존 및 장기기억 시스템으로 사용할 때 다음 속성이 훼손됩니다.

* 출처 추적성
* 재검증 가능성
* 감사 가능성
* 동일 Evidence 식별
* Source lineage
* Claim-Evidence 관계 검증

일반적인 공개 URL 자체는 비밀정보가 아닙니다.

다만 URL query parameter 안에 실제 인증정보가 포함될 수 있으므로, URL 전체를 삭제하는 것이 아니라 민감한 parameter 값만 부분적으로 마스킹해야 합니다.

예:

입력:

```text
https://example.com/article?id=123&access_token=SECRET
```

정상 결과:

```text
https://example.com/article?id=123&access_token=<REDACTED>
```

다음과 같은 일반 공개 URL은 그대로 보존해야 합니다.

```text
https://www.example.com/news/article/20260729/123456
https://example.com/article?id=12345
https://example.com/%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90
```

---

## 1.4 저장 성공과 데이터 품질 성공이 동일하게 취급됨

현재는 다음 조건을 만족하면 시스템이 정상으로 판정되는 것으로 보입니다.

* 파일 생성 성공
* Frontmatter 파싱 성공
* 청크 생성 성공
* FTS 색인 성공
* Vector 생성 성공
* Embedding 생성 성공
* DB 오류 없음

그러나 실제로는 다음과 같은 문서도 `indexed` 및 `READY` 상태가 될 수 있습니다.

```yaml
tags: "()"
source_of_truth: "true"
```

또는 공개 출처 URL이 손실된 문서도 정상 문서로 처리될 수 있습니다.

따라서 Alexandria의 운영 상태는 최소한 다음 두 계층을 구분해야 합니다.

### Infrastructure health

* 파일 접근 가능
* DB 연결 정상
* FTS 정상
* Vector 정상
* Embedding 정상
* 인덱스 stale 없음

### Data integrity health

* 필드 타입 정상
* 필수 메타데이터 존재
* Frontmatter schema 일치
* 태그 배열 정상
* 참조 배열 정상
* URL 비정상 손실 없음
* ID 및 lifecycle 필드 일관성
* 검색 필터 round-trip 성공

Infrastructure가 정상이라고 해서 문서의 데이터 품질까지 정상인 것은 아닙니다.

---

## 1.5 구조화 참조 필드의 활용 부족

실제 문서 본문에는 Evidence ID, Artifact ID 또는 Claim ID가 존재하지만 다음 Frontmatter 필드는 비어 있습니다.

```yaml
artifact_refs: []
evidence_refs: []
confidence: null
```

이 자체가 항상 오류는 아닙니다.

그러나 Alexandria가 `evidence_refs`, `artifact_refs` 등의 구조화 참조 필드를 공식 모델로 제공하고 있다면, 저장 API가 해당 값을 안전하게 전달하고 round-trip 할 수 있어야 합니다.

현재 확인이 필요한 부분은 다음과 같습니다.

* 참조 배열이 저장 API에서 실제 지원되는가
* tuple 또는 repr 문자열로 손실되지 않는가
* YAML 저장 후 배열 타입이 유지되는가
* 재색인 후 검색 결과 metadata에 유지되는가
* Graph 및 reconciliation 기능에서 사용되는가
* 빈 배열과 null의 의미가 구분되는가

본문을 임의로 정규식 파싱해 자동 Evidence를 생성하는 기능은 이번 수정의 필수 목표가 아닙니다.

우선 Alexandria가 명시적으로 받은 구조화 입력을 정확하게 보존할 수 있는지를 검증해 주세요.

---

# 2. 작업 목표

이번 작업의 핵심 목표는 다음과 같습니다.

> Alexandria-Hermes의 입력 스키마부터 Vault 파일, DB, RAG 검색 결과까지 이어지는 전체 데이터 round-trip에서 메타데이터의 타입과 의미가 손실되지 않도록 한다.

Evidence Intelligence 전용 코드나 경로 조건을 추가해서 문제를 우회하면 안 됩니다.

수정은 Alexandria에 저장되는 모든 문서에 공통으로 적용되어야 합니다.

대상 범위는 최소 다음을 포함합니다.

* Context
* Memory
* Vault Note
* Artifact
* Evidence reference
* 일반 Markdown 문서
* MCP를 통해 저장되는 문서
* HTTP API를 통해 저장되는 문서
* 내부 서비스가 직접 저장하는 문서

---

# 3. 작업 시작 절차

다음 순서로 조사하세요.

1. 저장소 규칙과 `AGENTS.md`를 읽습니다.
2. README, architecture, design, schema 및 migration 문서를 읽습니다.
3. 현재 브랜치와 `git status`, `git diff`, untracked 파일을 확인합니다.
4. 현재 작업 중인 변경사항이 있다면 덮어쓰지 않습니다.
5. MCP tool schema에서 문서 저장 요청이 어떻게 정의되는지 확인합니다.
6. HTTP API의 request DTO와 Pydantic 모델을 확인합니다.
7. service, repository, serializer, frontmatter writer까지 실제 호출 흐름을 추적합니다.
8. 파일을 다시 읽어 DB 또는 API response로 반환하는 역직렬화 흐름을 추적합니다.
9. reindex, chunking, embedding, metadata indexing 흐름을 확인합니다.
10. tag filter, metadata filter, path search 및 HYBRID search 구현을 확인합니다.
11. redaction 및 secret detection 로직을 확인합니다.
12. operational readiness가 어떤 조건만 검사하는지 확인합니다.

추측으로 수정하지 말고 실제 호출 경로를 문서화한 뒤 수정하세요.

---

# 4. 핵심 조사 질문

다음 질문에 코드 근거로 답해야 합니다.

## 4.1 태그가 어느 단계에서 손실되는가

가능한 원인 예시:

* MCP schema가 `list[str]`가 아니라 자유 형식을 허용
* Python tuple을 DTO가 그대로 허용
* serializer에서 `str(value)` 호출
* YAML dumper에 전달하기 전에 문자열로 강제 변환
* API connector가 JSON array 대신 tuple repr을 전송
* frontmatter parser가 tuple을 지원하지 못해 문자열로 보존
* DB column이 JSON이 아닌 text이며 별도 parsing이 없음

실제 원인을 확인하고 가장 앞단의 안전한 경계에서 수정하세요.

---

## 4.2 Boolean이 어느 단계에서 문자열로 바뀌는가

다음 흐름을 각각 확인하세요.

* request parsing
* DTO validation
* domain model
* metadata merge
* frontmatter serialization
* Markdown read-back
* DB persistence
* API response serialization

단순히 YAML 출력만 수정하지 말고 전체 round-trip에서 Boolean 타입을 검증하세요.

---

## 4.3 URL redaction은 어느 계층에서 수행되는가

확인 대상:

* MCP 입력 처리
* API request logging
* Context sanitization
* frontmatter sanitizer
* Markdown body sanitizer
* Vault writer
* response serializer

redaction이 보안 로그에만 적용되는지, 실제 Source of Truth 파일을 변경하는지도 구분하세요.

로그 출력에서 비밀정보를 숨기는 것과 원본 문서를 영구적으로 변형하는 것은 별개의 정책이어야 합니다.

---

## 4.4 `READY`가 의미하는 것은 무엇인가

현재 `READY`가 다음 중 무엇을 의미하는지 명확히 하세요.

1. 프로세스가 요청을 받을 수 있음
2. DB와 Vault에 접근 가능
3. RAG 인프라가 정상
4. 저장된 데이터의 schema 무결성까지 정상
5. 전체 기능이 운영 가능한 상태

현재 1~3만 검사한다면 응답 필드나 문서에서 그 의미를 명확히 해야 합니다.

데이터 품질까지 검사하지 않으면서 전체 시스템이 완전히 정상인 것처럼 표현하면 안 됩니다.

---

# 5. 필수 수정 사항

## 5.1 공통 Collection 필드 정규화

다음과 같은 collection 필드를 공통 방식으로 처리할 수 있는지 조사하세요.

* `tags`
* `artifact_refs`
* `evidence_refs`
* `conflict_set_ids`
* 기타 `list[str]` 또는 참조 배열 필드

지원 입력:

* `list[str]`
* `tuple[str, ...]`
* 단일 문자열
* `null`
* 빈 list
* 빈 tuple
* 기존에 잘못 저장된 tuple repr 문자열

예:

```python
("alpha", "beta")
```

정규화 결과:

```python
["alpha", "beta"]
```

다음 문자열도 legacy repair 단계에서 안전하게 복원할 수 있어야 합니다.

```text
"('alpha', 'beta')"
```

단, `eval`은 절대 사용하지 마세요.

필요하다면 `ast.literal_eval`을 사용하되 다음 조건을 만족해야 합니다.

* legacy repair 경로 또는 제한된 normalizer에서만 사용
* 결과 타입을 list 또는 tuple로 제한
* 각 원소가 문자열인지 검증
* nested collection 거부
* dict 또는 arbitrary object 거부
* 예상하지 못한 값은 validation error 처리

정규화 후 다음을 적용하세요.

* 공백 제거
* 빈 문자열 제거
* 원래 순서 유지
* 중복 제거
* 문자열로 다시 감싸지 않음

`"()"`는 `[]`로 처리합니다.

---

## 5.2 공통 Scalar 타입 정규화

Boolean으로 선언된 필드는 Boolean으로 유지해야 합니다.

허용 입력:

```text
true
false
"true"
"false"
```

대소문자는 허용할 수 있습니다.

다음 값은 자동 변환하지 말고 오류로 처리하세요.

```text
"yes"
"no"
"1"
"0"
"on"
"off"
"truthy"
```

숫자, 날짜, enum 등의 필드도 문자열로 무조건 변환하는 공통 코드가 있는지 확인하세요.

메타데이터 전체를 `dict[str, str]`로 처리하고 있다면 이것이 근본 원인일 수 있으므로 typed metadata 구조를 검토하세요.

---

## 5.3 안전한 URL redaction

redaction 정책을 다음과 같이 분리하세요.

### 보존 대상

* 일반 HTTPS URL
* 기사 URL
* 기업 IR URL
* 정부기관 URL
* 긴 path가 포함된 URL
* percent-encoded URL
* UUID가 포함된 URL
* 일반적인 article ID query parameter
* 공개 문서 링크

### 마스킹 대상

* API key
* access token
* refresh token
* bearer token
* password
* private key
* session secret
* 실제 인증 signature
* 명백한 credential query parameter

민감 query parameter 이름 예시:

```text
token
access_token
refresh_token
api_key
apikey
secret
client_secret
signature
sig
authorization
auth
password
passwd
session
session_token
```

URL 전체를 제거하지 말고 해당 parameter 값만 마스킹하세요.

또한 다음 두 정책을 분리하세요.

* 저장 원본 sanitization
* 로그 및 에러 응답 sanitization

로그에는 민감정보가 없어야 하지만, 일반 공개 Evidence URL이 Source of Truth 파일에서 손실되면 안 됩니다.

---

## 5.4 데이터 무결성 검증 계층 추가

저장 전에 schema validation을 수행하세요.

검증 대상 예시:

* collection 필드 타입
* Boolean 타입
* ID 타입
* status enum
* lifecycle enum
* 날짜 형식
* timezone을 포함해야 하는 datetime
* 참조 필드 배열
* 필수 title
* context type
* visibility 및 scope 일관성

프로젝트별 필드나 Evidence Intelligence 전용 ticker 규칙을 Alexandria core에 하드코딩하지 마세요.

도메인별 검증이 필요하다면 extension 또는 policy 계층으로 분리하세요.

Alexandria core에서는 범용 schema와 타입 무결성만 책임져야 합니다.

---

## 5.5 운영 상태와 데이터 품질 상태 분리

가능하다면 상태 모델을 다음처럼 구분하세요.

```json
{
  "operational_status": "READY",
  "infrastructure_health": "HEALTHY",
  "data_integrity_status": "DEGRADED",
  "warnings": [
    {
      "code": "INVALID_COLLECTION_SERIALIZATION",
      "count": 4
    }
  ]
}
```

반드시 이 정확한 응답 형태를 사용할 필요는 없습니다.

다만 다음을 구분할 수 있어야 합니다.

* 서비스 운영 가능 여부
* Vault 및 DB 무결성
* RAG 인프라 상태
* 저장 문서 schema 무결성
* legacy 문서 repair 필요 여부

데이터 무결성 문제가 있다고 서비스를 무조건 `NOT_READY`로 만들 필요는 없습니다.

대신 `READY_WITH_WARNINGS`, `DEGRADED` 또는 별도 필드 등 현재 아키텍처에 맞는 표현을 선택하세요.

---

# 6. Legacy 문서 Repair

이미 잘못 저장된 문서가 존재합니다.

예:

```yaml
tags: "()"
```

```yaml
tags: "('Evidence Intelligence', 'Closing Review v3', 'Market')"
```

```yaml
source_of_truth: "true"
```

기존 문서를 무조건 전체 덮어쓰지 말고 안전한 repair workflow를 설계하세요.

## 필수 동작

1. 문제 문서 탐색
2. 원본 경로 출력
3. 문제가 있는 필드 출력
4. 기존 값 출력
5. 제안하는 수정 값 출력
6. 기본 동작은 dry-run
7. 명시적 apply 옵션에서만 수정
8. 본문 내용은 변경하지 않음
9. 기존 ID와 path 유지
10. 수정 후 대상 문서 재색인
11. 수정 전후 content hash 변화 보고
12. 성공·실패 문서 수 보고

공개 URL이 이미 `<REDACTED_LONG_VALUE>`로 저장된 경우 원 URL을 추측해 복구하지 마세요.

원본 요청 payload, audit log 또는 이전 artifact 등 신뢰할 수 있는 출처에서 정확한 값을 찾을 수 있을 때만 복구하세요.

복구할 수 없다면 다음처럼 보고하세요.

```text
unrecoverable_redacted_urls: 7
```

---

# 7. 재현 사례

Evidence Intelligence는 이번 Alexandria 문제를 발견한 dogfooding 사례로 사용합니다.

다음과 같은 일반적인 Context를 저장하는 통합 테스트 fixture를 만드세요.

```yaml
title: "Dogfood Metadata Round Trip"
project: "Evidence Intelligence"
report: "Closing Review v3"
date: "2026-07-29"
source_of_truth: true
tags:
  - Evidence Intelligence
  - Closing Review v3
  - Market
  - KRX
  - "2026-07-29"
evidence_refs:
  - E-MKT-001
  - E-MKT-002
artifact_refs: []
```

본문에는 다음과 같은 일반 공개 URL을 포함합니다.

```text
https://example.com/news/2026/07/29/article-123
https://example.com/article?id=12345
https://example.com/article?id=12345&access_token=SECRET
```

저장 후 다음이 성립해야 합니다.

* tags는 YAML 배열
* `source_of_truth`는 Boolean
* `evidence_refs`는 배열
* 일반 공개 URL은 보존
* `access_token` 값만 마스킹
* read-back 후 타입 유지
* DB metadata 타입 유지
* reindex 후 타입 유지
* tag filter 검색 성공
* project filter 검색 성공
* HYBRID 검색 성공

테스트와 core 구현에서 `Evidence Intelligence`라는 프로젝트명에 의존하는 조건문을 추가하면 안 됩니다.

이 fixture는 범용 동작을 검증하는 예시일 뿐입니다.

---

# 8. 테스트 요구사항

## 8.1 Collection normalizer

다음을 테스트하세요.

* 정상 `list[str]`
* tuple 입력
* 단일 문자열
* 빈 list
* 빈 tuple
* `null`
* tuple repr 문자열
* `"()"` 문자열
* 중복 제거
* 공백 제거
* 빈 원소 제거
* nested list 거부
* dict 거부
* 숫자 원소 거부
* arbitrary repr 거부

---

## 8.2 Boolean round-trip

다음을 테스트하세요.

* `True`
* `False`
* `"true"`
* `"false"`
* 대소문자 혼합
* `"yes"` 거부
* `"1"` 거부
* 숫자 `1` 처리 정책 명시
* YAML dump 후 Boolean 유지
* YAML load 후 Boolean 유지
* API response 후 Boolean 유지

---

## 8.3 URL redaction

다음을 테스트하세요.

* 일반 기사 URL 보존
* 긴 URL 보존
* percent-encoded URL 보존
* UUID URL 보존
* 일반 query parameter 보존
* `access_token` 값만 마스킹
* `api_key` 값만 마스킹
* Authorization header 마스킹
* Bearer token 마스킹
* private key 마스킹
* 일반 URL 전체를 `<REDACTED_LONG_VALUE>`로 바꾸지 않음
* fragment와 query parameter 순서 보존

---

## 8.4 참조 필드

다음을 테스트하세요.

* `evidence_refs` 배열 저장
* `artifact_refs` 배열 저장
* 빈 배열 저장
* null 처리 정책
* 중복 제거 여부
* 순서 유지
* reindex 후 유지
* API read-back 후 유지
* 검색 metadata에서 유지

---

## 8.5 검색

다음 검색 유형을 검증하세요.

* title 검색
* path 검색
* project 필터
* metadata 검색
* 단일 tag 필터
* 복수 tag 필터
* 날짜 문자열 검색
* FTS 검색
* Vector 검색
* HYBRID 검색

path search 함수가 실제 path 문자열만 검색하는 설계라면, title과 metadata까지 검색하는 것처럼 오해되지 않도록 함수명 또는 설명을 수정하세요.

---

## 8.6 Operational status

다음 상태를 테스트하세요.

1. 인프라와 데이터 모두 정상
2. 인프라는 정상이나 legacy metadata 문제 존재
3. DB 오류
4. embedding stale 존재
5. Vault index error 존재
6. repair 대상 문서 존재
7. redaction 손실 문서 존재

각 상태가 어떤 readiness 또는 warning 결과를 반환해야 하는지 명시하세요.

---

# 9. 실제 검증 절차

수정 후 다음 순서로 검증하세요.

1. 관련 unit test
2. integration test
3. serializer round-trip test
4. metadata migration test
5. redaction regression test
6. 검색 regression test
7. lint
8. format check
9. typecheck
10. 전체 테스트
11. dogfood fixture 저장
12. 저장 문서 원본 확인
13. API read-back 확인
14. tag filter 확인
15. project filter 확인
16. reindex 실행
17. RAG status 확인
18. embedding fingerprint 확인
19. operational readiness 확인
20. data integrity status 또는 warning 확인

가능하다면 실제 Alexandria 도구 또는 대응 API를 사용하세요.

* `alexandria_save_note`
* `alexandria_read_note`
* `alexandria_search_vault`
* `alexandria_librarian_vault_path_search`
* `alexandria_reindex_vault`
* `alexandria_rag_status`
* `alexandria_operational_readiness`

---

# 10. 완료 조건

다음 조건을 모두 만족해야 완료입니다.

* collection 타입이 저장 과정에서 문자열로 손실되지 않음
* tags가 실제 YAML 배열로 저장됨
* `"()"`가 저장되지 않음
* tuple repr 문자열이 신규 저장에서 발생하지 않음
* Boolean 필드가 Boolean으로 유지됨
* 일반 공개 URL이 보존됨
* 실제 credential만 부분 마스킹됨
* 구조화 참조 배열이 round-trip에서 유지됨
* tag filter가 정상 작동함
* reindex 후 metadata 타입이 유지됨
* 기존 정상 문서의 ID, path, 본문이 훼손되지 않음
* legacy repair가 dry-run과 apply로 분리됨
* Infrastructure health와 Data integrity 상태가 구분됨
* 특정 프로젝트 전용 예외 처리 없이 범용적으로 해결됨

---

# 11. 결과 보고 형식

작업 완료 후 다음 순서로 보고하세요.

## 1. Dogfooding 피드백 요약

사용 과정에서 어떤 문제가 드러났는지 설명합니다.

## 2. 근본 원인

각 문제가 발생한 정확한 코드 경로를 제시합니다.

예:

```text
MCP request
→ SaveContextRequest
→ metadata normalizer
→ frontmatter serializer
→ Vault writer
```

## 3. 수정한 파일

파일별 변경 목적을 설명합니다.

## 4. 핵심 설계 변경

다음을 구분합니다.

* 입력 정규화
* schema validation
* serialization
* redaction
* 검색 metadata
* readiness 및 integrity reporting
* legacy repair

## 5. 테스트 결과

실행한 명령과 결과를 보고합니다.

## 6. 실제 dogfood 검증

실제 문서를 저장하고 읽고 검색한 결과를 보여줍니다.

## 7. Migration 또는 repair 결과

다음을 포함합니다.

* 탐색 문서 수
* repair 대상 수
* 수정 성공 수
* 수정 실패 수
* 복구 불가능 URL 수
* 재색인 결과

## 8. 남은 제한 사항

이번 수정 범위 밖의 문제를 명확하게 기록합니다.

## 9. 실패 내역

실패가 있었다면 숨기지 말고 다음을 그대로 포함합니다.

* 실패한 함수 또는 명령
* 입력 또는 주요 인자
* HTTP status 또는 exit code
* 실제 error response 또는 stderr
* 재시도 여부
* 최종 해결 여부

---

# 12. 작업 제한

* Evidence Intelligence 전용 조건문을 추가하지 마세요.
* 특정 날짜나 특정 문서 경로를 하드코딩하지 마세요.
* 기존 문서를 삭제하지 마세요.
* hard delete를 수행하지 마세요.
* 원본 URL을 추측해 복원하지 마세요.
* `eval`을 사용하지 마세요.
* 모든 metadata를 문자열로 강제 변환하지 마세요.
* `Any`로 타입 문제를 숨기지 마세요.
* validation을 약화해 테스트만 통과시키지 마세요.
* 기존 정상 문서의 본문을 불필요하게 다시 작성하지 마세요.
* 전체 Vault를 무조건 덮어쓰지 마세요.
* 현재 작업 중인 사용자 변경사항을 되돌리지 마세요.
* 사용자 요청 없이 commit 또는 push하지 마세요.
* 실제 실행하지 않은 테스트를 성공했다고 보고하지 마세요.
* 저장 성공을 데이터 무결성 성공과 동일하게 취급하지 마세요.
