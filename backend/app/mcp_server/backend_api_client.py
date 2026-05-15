"""Async HTTP backend client for Alexandria-Hermes MCP tools."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from app.platform.security.operator_api_key import OPERATOR_API_KEY_HEADER
from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONObject, JSONValue

DEFAULT_ALEXANDRIA_API_URL = "http://localhost:8000"
DEFAULT_MCP_TIMEOUT_SECONDS = 30.0

HttpHeaders = dict[str, str]


@dataclass(frozen=True, slots=True, kw_only=True)
class AlexandriaApiSettings:
    """Environment-backed settings for the MCP HTTP client."""

    base_url: str = DEFAULT_ALEXANDRIA_API_URL
    api_token: str | None = None
    operator_api_key: str | None = None
    timeout: float = DEFAULT_MCP_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> AlexandriaApiSettings:
        """Create settings from MCP environment variables.

        Args:
            None.

        Returns:
            Client settings for backend API calls.
        """
        alexandria_url = os.environ.get("ALEXANDRIA_API_URL")
        hermes_url = os.environ.get("HERMES_API_URL")
        if alexandria_url is not None and alexandria_url != "":
            base_url = alexandria_url
        elif hermes_url is not None and hermes_url != "":
            base_url = hermes_url
        else:
            base_url = DEFAULT_ALEXANDRIA_API_URL
        raw_token = os.environ.get("ALEXANDRIA_API_TOKEN")
        if raw_token is not None and raw_token != "":
            token: str | None = raw_token
        else:
            token = None
        raw_operator_key = os.environ.get("ALEXANDRIA_OPERATOR_API_KEY")
        if raw_operator_key is None or raw_operator_key == "":
            raw_operator_key = os.environ.get("SERVICE_OPERATOR_API_KEY")
        if raw_operator_key is None or raw_operator_key == "":
            raw_operator_key = raw_token
        if raw_operator_key is not None and raw_operator_key != "":
            operator_key: str | None = raw_operator_key
        else:
            operator_key = None
        raw_timeout = os.environ.get("ALEXANDRIA_API_TIMEOUT_SECONDS")
        timeout = DEFAULT_MCP_TIMEOUT_SECONDS
        if raw_timeout is not None:
            try:
                timeout = max(1.0, float(raw_timeout))
            except ValueError as exc:
                message = "ALEXANDRIA_API_TIMEOUT_SECONDS must be numeric"
                raise AlexandriaApiConfigurationError(message) from exc
        settings = cls(
            base_url=base_url.rstrip("/"),
            api_token=token,
            operator_api_key=operator_key,
            timeout=timeout,
        )
        return settings


class AlexandriaApiConfigurationError(Exception):
    """Invalid MCP backend API configuration."""


class AlexandriaApiError(Exception):
    """Backend HTTP error surfaced to MCP tools."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize an API error.

        Args:
            status_code: HTTP status code or zero for transport failures.
            message: Stable error message.

        Returns:
            None.
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class AlexandriaApiClient:
    """Native async HTTP client for backend API calls from MCP tools."""

    def __init__(
        self,
        settings: AlexandriaApiSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            settings: Backend API settings.
            transport: Optional async HTTP transport for tests.

        Returns:
            None.
        """
        self._settings = settings
        self._transport = transport

    async def get(self, path: str, params: JSONObject | None = None) -> JSONValue:
        """Send a GET request to the backend.

        Args:
            path: Backend path beginning with slash.
            params: Optional query parameters.

        Returns:
            Decoded JSON response.
        """
        payload = await self._request("GET", path, None, params)
        return payload

    async def post(self, path: str, payload: JSONObject) -> JSONValue:
        """Send a POST request to the backend.

        Args:
            path: Backend path beginning with slash.
            payload: JSON request body.

        Returns:
            Decoded JSON response.
        """
        response = await self._request("POST", path, payload, None)
        return response

    async def _request(
        self,
        method: str,
        path: str,
        payload: JSONValue | None,
        params: JSONObject | None,
    ) -> JSONValue:
        request_body = None if payload is None else dumps_json(payload)
        headers: HttpHeaders = {"Accept": "application/json"}
        if request_body is not None:
            headers["Content-Type"] = "application/json"
        if self._settings.api_token:
            headers["Authorization"] = f"Bearer {self._settings.api_token}"
        if self._settings.operator_api_key:
            headers[OPERATOR_API_KEY_HEADER] = self._settings.operator_api_key
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=httpx.Timeout(self._settings.timeout),
                transport=self._transport,
            ) as client:
                response = await client.request(
                    method,
                    path,
                    params=_query_params(params),
                    content=request_body,
                    headers=headers,
                )
        except httpx.RequestError as exc:
            message = str(exc)
            raise AlexandriaApiError(0, message) from exc
        if response.status_code < 200 or response.status_code >= 300:
            message = _error_message(response.content)
            raise AlexandriaApiError(response.status_code, message)
        decoded = _decode_json(response.content)
        return decoded


def _query_params(params: JSONObject | None) -> dict[str, str]:
    if params is None:
        return {}
    compact = {
        key: str(value)
        for key, value in params.items()
        if value is not None and not isinstance(value, list | dict)
    }
    return compact


def _decode_json(body: bytes) -> JSONValue:
    if not body:
        return None
    decoded = loads_json(body)
    return decoded


def _error_message(body: bytes) -> str:
    try:
        payload = _decode_json(body)
    except ValueError:
        decoded_body = body.decode("utf-8", errors="replace")
        message = "request failed" if decoded_body == "" else decoded_body
        return message
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail is None:
            detail = payload.get("message")
        if isinstance(detail, str):
            return detail
    return "request failed"
