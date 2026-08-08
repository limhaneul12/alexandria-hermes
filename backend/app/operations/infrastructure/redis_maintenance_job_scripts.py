"""Lua scripts used by the Redis maintenance queue adapter."""

from __future__ import annotations

from typing import Final

ENQUEUE_MAINTENANCE_JOB_SCRIPT: Final[str] = """
local existing = redis.call('GET', KEYS[1])
if existing then
  return {'DEDUPLICATED', existing, ''}
end

local current = redis.call('INCR', KEYS[4])
if current == 1 then
  redis.call('EXPIRE', KEYS[4], ARGV[1])
end
if current > tonumber(ARGV[2]) then
  local ttl = redis.call('TTL', KEYS[4])
  return {'RATE_LIMITED', tostring(ttl), ''}
end

local stream_id = redis.call(
  'XADD', KEYS[2], 'MAXLEN', '~', ARGV[3], '*',
  'job_id', ARGV[4],
  'kind', ARGV[5],
  'requested_by', ARGV[6],
  'source_id', ARGV[7],
  'limit', ARGV[8],
  'force', ARGV[9],
  'submitted_at', ARGV[10]
)
redis.call(
  'HSET', KEYS[3],
  'job_id', ARGV[4],
  'kind', ARGV[5],
  'status', 'QUEUED',
  'requested_by', ARGV[6],
  'source_id', ARGV[7],
  'limit', ARGV[8],
  'force', ARGV[9],
  'attempts', '0',
  'submitted_at', ARGV[10],
  'stream_id', stream_id,
  'result_json', '',
  'error_summary', ''
)
redis.call('EXPIRE', KEYS[3], ARGV[11])
redis.call('SET', KEYS[1], ARGV[4], 'EX', ARGV[12])
return {'QUEUED', ARGV[4], stream_id}
"""
