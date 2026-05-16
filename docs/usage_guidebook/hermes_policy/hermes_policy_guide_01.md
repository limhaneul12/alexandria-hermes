# Hermes Policy Guide 01 — Alexandria 사용 ON/OFF

## 목적

사용자가 Hermes에게 Alexandria-Hermes를 쓰게 할지 말지를 명확히 제어한다.

## policy 위치

```text
~/.hermes/alexandria-hermes/policy.yaml
```

기본값은 ON이다.

```yaml
enabled: true
mode: autonomous
```

## 상태 확인

```bash
alexandria-hermes --json hermes policy status --hermes-home "$HOME/.hermes"
```

예상 출력 일부:

```json
{
  "enabled": true,
  "mode": "autonomous",
  "self_acquisition_enabled": true,
  "librarian_optional": true,
  "hermes_self_acquisition_fallback": true
}
```

## 끄기

```bash
alexandria-hermes --json hermes policy disable --hermes-home "$HOME/.hermes"
```

이후 Hermes는 다음 경우를 제외하고 Alexandria를 쓰지 않아야 한다.

- status/diagnostics 확인
- 사용자가 명시적으로 Alexandria 사용을 요청한 경우

## 다시 켜기

```bash
alexandria-hermes --json hermes policy enable --hermes-home "$HOME/.hermes"
```

## Hermes에게 말하는 예

```text
Alexandria 사용하지 마.
```

Hermes가 해야 할 일:

```bash
alexandria-hermes hermes policy disable
```

```text
다시 Alexandria 써.
```

Hermes가 해야 할 일:

```bash
alexandria-hermes hermes policy enable
```

## session-only off

아래 표현은 global policy를 바꾸지 않고 현재 작업에서만 적용한다.

```text
이번 작업에서는 Alexandria 쓰지 말고 해.
```

이 경우 Hermes는 현재 task/session에서만 Alexandria tool을 피하고, `policy.yaml`은 수정하지 않는다.
