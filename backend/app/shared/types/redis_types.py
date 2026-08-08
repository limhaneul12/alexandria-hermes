"""Narrow recursive value contracts for redis-py command responses."""

from __future__ import annotations

type RedisKey = str | bytes
type RedisScalarResponse = str | bytes | int | float | bool | None
type RedisResponse = (
    RedisScalarResponse
    | list[RedisResponse]
    | tuple[RedisResponse, ...]
    | dict[RedisKey, RedisResponse]
)
type RedisHashResponse = dict[RedisKey, RedisResponse]
