"""Local operator approval page for self-hosted MCP OAuth."""

from __future__ import annotations

from html import escape
from typing import Final

from mcp.server.fastmcp import FastMCP
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from app.mcp_server.local_oauth.provider import (
    LocalMcpOAuthProvider,
    LocalOAuthApprovalError,
)

_SECURITY_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Content-Security-Policy": (
        "default-src 'none'; form-action 'self'; base-uri 'none'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def register_local_oauth_approval_route(
    server: FastMCP,
    provider: LocalMcpOAuthProvider,
) -> None:
    """Register the public browser approval route on one FastMCP server.

    Args:
        server: FastMCP server receiving standard OAuth routes.
        provider: Local authorization provider owning pending approvals.
    """

    @server.custom_route(
        "/approve",
        methods=["GET", "POST"],
        name="local_mcp_oauth_approval",
        include_in_schema=False,
    )
    async def local_mcp_oauth_approval(request: Request) -> Response:
        if request.method == "GET":
            request_id = request.query_params.get("request_id", "")
            try:
                pending = await provider.pending_authorization(request_id)
            except LocalOAuthApprovalError as exc:
                return _error_response(exc)
            return HTMLResponse(
                _approval_html(
                    request_id=pending.request_id,
                    client_name=pending.client_name or "ChatGPT MCP client",
                    scopes=pending.scopes,
                ),
                headers=_SECURITY_HEADERS,
            )
        form = await request.form()
        request_id = _form_text(form.get("request_id"))
        operator_key = _form_text(form.get("operator_key"))
        decision = _form_text(form.get("decision"))
        try:
            if decision == "approve":
                redirect_url = await provider.approve_authorization(
                    request_id=request_id,
                    operator_key=operator_key,
                )
            elif decision == "deny":
                redirect_url = await provider.deny_authorization(
                    request_id=request_id,
                    operator_key=operator_key,
                )
            else:
                raise LocalOAuthApprovalError(400, "OAuth decision is invalid")
        except LocalOAuthApprovalError as exc:
            return _error_response(exc)
        return RedirectResponse(
            redirect_url,
            status_code=302,
            headers=_SECURITY_HEADERS,
        )


def _approval_html(
    *,
    request_id: str,
    client_name: str,
    scopes: tuple[str, ...],
) -> str:
    safe_request_id = escape(request_id, quote=True)
    safe_client_name = escape(client_name)
    safe_scopes = ", ".join(escape(scope) for scope in scopes)
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Approve Alexandria MCP</title></head>
<body>
  <main>
    <h1>Approve Alexandria-Hermes MCP access</h1>
    <p>Client: <strong>{safe_client_name}</strong></p>
    <p>Scopes: <code>{safe_scopes}</code></p>
    <p>This approval grants access to your local Alexandria memory tools.</p>
    <form method="post" action="/approve" autocomplete="off">
      <input type="hidden" name="request_id" value="{safe_request_id}">
      <label>Local operator approval key
        <input type="password" name="operator_key" required autofocus>
      </label>
      <button type="submit" name="decision" value="approve">Approve</button>
      <button type="submit" name="decision" value="deny">Deny</button>
    </form>
  </main>
</body>
</html>"""


def _error_response(exc: LocalOAuthApprovalError) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><body><h1>OAuth approval failed</h1>"
        f"<p>{escape(exc.detail)}</p></body></html>",
        status_code=exc.status_code,
        headers=_SECURITY_HEADERS,
    )


def _form_text(value: str | UploadFile | None) -> str:
    return value if isinstance(value, str) else ""
