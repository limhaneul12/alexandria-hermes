"""External API Redis budget and wiring contracts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import anyio
from redis.asyncio import Redis

from app.operations.infrastructure.redis_fixed_window_rate_limiter import (
    RedisFixedWindowRateLimiter,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = BACKEND_ROOT / "app"
_DIRECT_OPENAI_CALL = re.compile(
    r"\bawait\b.*\.(?:responses|embeddings)\.create\(|"
    r"\bawait\b.*\.chat\.completions\.create\("
)


class _FakeRedis:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[object, ...]] = []

    async def eval(self, *args: object) -> object:
        self.calls.append(args)
        return self.response


def test_fixed_window_limiter_reports_remaining_and_retry_delay() -> None:
    """Redis script responses should map to a stable provider-budget decision."""

    async def scenario() -> tuple[bool, int, int]:
        fake = _FakeRedis([3, 41])
        decision = await RedisFixedWindowRateLimiter(
            client=cast(Redis, fake),
            key_prefix="alexandria:rate:v1",
        ).acquire(
            scope="external-api:openai",
            subject="caller-hash",
            limit=5,
            window_seconds=60,
        )
        return (
            decision.allowed,
            decision.remaining,
            decision.retry_after_seconds,
        )

    assert anyio.run(scenario) == (True, 2, 41)


def test_fixed_window_limiter_denies_after_limit() -> None:
    """Counts above the configured budget should be rejected until key expiry."""

    async def scenario() -> tuple[bool, int, int]:
        fake = _FakeRedis([6, 17])
        decision = await RedisFixedWindowRateLimiter(
            client=cast(Redis, fake),
            key_prefix="alexandria:rate:v1",
        ).acquire(
            scope="external-api:openai",
            subject="caller-hash",
            limit=5,
            window_seconds=60,
        )
        return (
            decision.allowed,
            decision.remaining,
            decision.retry_after_seconds,
        )

    assert anyio.run(scenario) == (False, 0, 17)


def test_direct_async_openai_calls_have_a_nearby_redis_budget_guard() -> None:
    """Direct provider calls must consume a Redis permit before network activity."""
    failures: list[str] = []
    matches = 0
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path.name == "external_api_rate_limit.py":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not _DIRECT_OPENAI_CALL.search(line):
                continue
            matches += 1
            nearby = "\n".join(lines[max(0, index - 6) : index])
            if "enforce_external_api_rate_limit(" not in nearby:
                failures.append(f"{path.relative_to(BACKEND_ROOT)}:{index + 1}")
    assert not failures, "unguarded OpenAI calls: " + ", ".join(failures)
    assert matches >= 0
