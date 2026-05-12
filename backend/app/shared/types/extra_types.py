"""Shared type alias module."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

JSONPrimitive = str | int | float | bool | None | datetime
type JSONValue = JSONPrimitive | Sequence[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
