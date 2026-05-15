"""HTTP transport boundary for the Alexandria-Hermes CLI."""

from __future__ import annotations

import urllib.error
import urllib.request

from app.cli_support.contracts.runtime_contracts import (
    CommandContext,
    HttpHeaders,
    HttpResponse,
)
from app.cli_support.routing.url_paths import join_url
from app.cli_support.serialization.json_payloads import (
    decode_json,
    error_message,
    json_bytes,
)
from app.shared.exceptions.cli_exceptions import CliRequestError
from app.shared.types.extra_types import JSONValue


class CliBackendApiClient:
    """Send synchronous backend HTTP requests for CLI command execution."""

    def __init__(self, context: CommandContext) -> None:
        """Initialize the CLI backend client.

        Args:
            context: Runtime context containing base URL, transport, and timeout.
        """
        self._context = context

    def get(self, path: str) -> JSONValue:
        """Send a GET request to the backend.

        Args:
            path: Backend API path beginning with slash.

        Returns:
            Decoded JSON response payload.
        """
        payload = self._request("GET", path, None)
        return payload

    def post(self, path: str, payload: JSONValue) -> JSONValue:
        """Send a POST request to the backend.

        Args:
            path: Backend API path beginning with slash.
            payload: JSON-compatible request payload.

        Returns:
            Decoded JSON response payload.
        """
        response = self._request("POST", path, payload)
        return response

    def delete(self, path: str) -> JSONValue:
        """Send a DELETE request to the backend.

        Args:
            path: Backend API path beginning with slash.

        Returns:
            Decoded JSON response payload.
        """
        response = self._request("DELETE", path, None)
        return response

    def _request(self, method: str, path: str, payload: JSONValue | None) -> JSONValue:
        url = join_url(self._context.base_url, path)
        request_body = None if payload is None else json_bytes(payload)
        headers: HttpHeaders = {"Accept": "application/json"}
        if request_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            status_code, response_body = self._context.transport(
                method,
                url,
                request_body,
                headers,
                self._context.timeout,
            )
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            response_body = exc.read()
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            raise CliRequestError(0, reason) from exc
        if status_code < 200 or status_code >= 300:
            message = error_message(response_body)
            raise CliRequestError(status_code, message)
        response = decode_json(response_body)
        return response


def default_transport(
    method: str,
    url: str,
    body: bytes | None,
    headers: HttpHeaders,
    timeout: float,
) -> HttpResponse:
    """Send one HTTP request using the standard library.

    Args:
        method: HTTP method.
        url: Fully qualified request URL.
        body: Optional encoded JSON request body.
        headers: Request headers.
        timeout: Network timeout in seconds.

    Returns:
        Status code and response body bytes.
    """
    request = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status_code = response.status
        response_body = response.read()
    return status_code, response_body
