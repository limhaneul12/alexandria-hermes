"""Command line interface for Alexandria-Hermes HTTP operations."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from app.shared.types.extra_types import JSONObject, JSONValue

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_SECONDS = 30.0

HttpHeaders = dict[str, str]
HttpResponse = tuple[int, bytes]
HttpTransport = Callable[[str, str, bytes | None, HttpHeaders, float], HttpResponse]


@dataclass(frozen=True, slots=True)
class CommandContext:
    base_url: str
    json_output: bool
    timeout: float
    stdout: TextIO
    stderr: TextIO
    transport: HttpTransport


class CliRequestError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class HermesHttpClient:
    def __init__(self, context: CommandContext) -> None:
        self._context = context

    def get(self, path: str) -> JSONValue:
        payload = self._request("GET", path, None)
        return payload

    def post(self, path: str, payload: JSONValue) -> JSONValue:
        response = self._request("POST", path, payload)
        return response

    def delete(self, path: str) -> JSONValue:
        response = self._request("DELETE", path, None)
        return response

    def _request(self, method: str, path: str, payload: JSONValue | None) -> JSONValue:
        url = _join_url(self._context.base_url, path)
        request_body = None if payload is None else _json_bytes(payload)
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
            message = _error_message(response_body)
            raise CliRequestError(status_code, message)
        response = _decode_json(response_body)
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


def build_parser() -> argparse.ArgumentParser:
    """Build the Hermes CLI parser.

    Args:
        None.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="alexandria-hermes",
        description="Alexandria-Hermes command line client",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("HERMES_API_URL", DEFAULT_API_URL),
        help="Backend API URL. Defaults to HERMES_API_URL or http://localhost:8000.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    health_parser = subcommands.add_parser("health", help="Check backend health")
    health_parser.set_defaults(handler="health")

    skills_parser = subcommands.add_parser("skills", help="Manage skill records")
    skill_commands = skills_parser.add_subparsers(dest="skill_command", required=True)
    skills_list = skill_commands.add_parser("list", help="List registered skills")
    skills_list.add_argument("--limit", type=int, default=20)
    skills_list.add_argument("--offset", type=int, default=0)
    skills_list.set_defaults(handler="skills_list")

    skills_get = skill_commands.add_parser("get", help="Read one skill")
    skills_get.add_argument("item_id")
    skills_get.set_defaults(handler="skills_get")

    skills_create = skill_commands.add_parser("create", help="Create a manual skill")
    skills_create.add_argument("--title", required=True)
    skills_create.add_argument("--purpose", required=True)
    skills_create.add_argument("--content")
    skills_create.add_argument("--content-file")
    skills_create.add_argument("--summary")
    skills_create.add_argument("--category-id")
    skills_create.add_argument("--tag", action="append", default=[])
    skills_create.add_argument("--tool", action="append", default=[])
    skills_create.add_argument("--usage-example")
    skills_create.add_argument(
        "--risk-level", default="LOW", choices=["LOW", "MEDIUM", "HIGH"]
    )
    skills_create.add_argument("--version", default="1.0.0")
    skills_create.add_argument("--created-by", default="Hermes CLI")
    skills_create.add_argument("--active", action="store_true")
    skills_create.set_defaults(handler="skills_create")

    skills_delete = skill_commands.add_parser("delete", help="Delete a skill")
    skills_delete.add_argument("item_id")
    skills_delete.set_defaults(handler="skills_delete")

    prompts_parser = subcommands.add_parser("prompts", help="Manage prompt records")
    prompt_commands = prompts_parser.add_subparsers(
        dest="prompt_command", required=True
    )
    prompts_list = prompt_commands.add_parser("list", help="List registered prompts")
    prompts_list.add_argument("--limit", type=int, default=20)
    prompts_list.add_argument("--offset", type=int, default=0)
    prompts_list.add_argument("--kind")
    prompts_list.add_argument("--tag")
    prompts_list.set_defaults(handler="prompts_list")

    prompts_get = prompt_commands.add_parser("get", help="Read one prompt")
    prompts_get.add_argument("item_id")
    prompts_get.set_defaults(handler="prompts_get")

    prompts_create = prompt_commands.add_parser("create", help="Create a prompt")
    prompts_create.add_argument("--title", required=True)
    prompts_create.add_argument("--summary")
    prompts_create.add_argument("--content")
    prompts_create.add_argument("--content-file")
    prompts_create.add_argument("--kind", default="USER_TEMPLATE")
    prompts_create.add_argument("--domain", default="GENERAL")
    prompts_create.add_argument("--task-type", default="GENERAL_TASK")
    prompts_create.add_argument(
        "--format", default="MARKDOWN", choices=["MARKDOWN", "XML", "JSON", "TEXT"]
    )
    prompts_create.add_argument("--var", action="append", default=[])
    prompts_create.add_argument("--output-format")
    prompts_create.add_argument("--target-actor")
    prompts_create.add_argument("--target-model-family")
    prompts_create.add_argument("--language")
    prompts_create.add_argument("--related-item-id", action="append", default=[])
    prompts_create.add_argument("--category-id")
    prompts_create.add_argument("--tag", action="append", default=[])
    prompts_create.add_argument("--version", default="1.0.0")
    prompts_create.add_argument("--created-by", default="Hermes CLI")
    prompts_create.add_argument(
        "--created-by-type", default="USER", choices=["USER", "AGENT", "LIBRARIAN"]
    )
    prompts_create.add_argument(
        "--source-type",
        default="USER_CREATED",
        choices=["USER_CREATED", "AGENT_SUBMITTED", "LIBRARIAN_CREATED", "IMPORTED"],
    )
    prompts_create.add_argument("--active", action="store_true")
    prompts_create.set_defaults(handler="prompts_create")

    prompts_use = prompt_commands.add_parser(
        "use", help="Print a prompt and record usage"
    )
    prompts_use.add_argument("item_id")
    prompts_use.add_argument("--actor-id")
    prompts_use.add_argument("--actor-name", default="Hermes CLI")
    prompts_use.set_defaults(handler="prompts_use")

    folders_parser = subcommands.add_parser("folders", help="Manage library folders")
    folder_commands = folders_parser.add_subparsers(
        dest="folder_command", required=True
    )
    folders_list = folder_commands.add_parser("list", help="List folders")
    folders_list.add_argument("--tree", action="store_true", help="Show nested tree")
    folders_list.set_defaults(handler="folders_list")

    folders_create = folder_commands.add_parser("create", help="Create a folder")
    folders_create.add_argument("--name", required=True)
    folders_create.add_argument("--parent-id")
    folders_create.set_defaults(handler="folders_create")

    folders_delete = folder_commands.add_parser("delete", help="Delete a folder")
    folders_delete.add_argument("folder_id")
    folders_delete.set_defaults(handler="folders_delete")

    library_parser = subcommands.add_parser("library", help="Browse library items")
    library_commands = library_parser.add_subparsers(
        dest="library_command", required=True
    )
    library_list = library_commands.add_parser("list", help="List all library items")
    library_list.add_argument("--limit", type=int, default=20)
    library_list.add_argument("--offset", type=int, default=0)
    library_list.add_argument(
        "--type", choices=["SKILL", "PROMPT", "WORKFLOW", "KNOWLEDGE"]
    )
    library_list.add_argument("--folder-id")
    library_list.add_argument("--query")
    library_list.set_defaults(handler="library_list")

    library_search = library_commands.add_parser("search", help="Search library items")
    library_search.add_argument("query")
    library_search.set_defaults(handler="library_search")

    minio_parser = subcommands.add_parser("minio", help="Sync external MINIO archive")
    minio_commands = minio_parser.add_subparsers(dest="minio_command", required=True)
    minio_scan = minio_commands.add_parser("scan", help="Preview import candidates")
    minio_scan.add_argument("--limit", type=int, default=24)
    minio_scan.add_argument(
        "--type", choices=["SKILL", "PROMPT", "WORKFLOW", "KNOWLEDGE"]
    )
    minio_scan.set_defaults(handler="minio_scan")

    minio_import = minio_commands.add_parser("import", help="Import linked candidates")
    minio_import.add_argument("--limit", type=int, default=48)
    minio_import.add_argument(
        "--type", choices=["SKILL", "PROMPT", "WORKFLOW", "KNOWLEDGE"]
    )
    minio_import.set_defaults(handler="minio_import")
    return parser


def run(
    argv: Sequence[str] | None = None,
    transport: HttpTransport | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the Hermes CLI.

    Args:
        argv: Optional argument sequence excluding program name.
        transport: Optional HTTP transport override for tests.
        stdout: Optional output stream.
        stderr: Optional error stream.

    Returns:
        Process-style exit code.
    """
    parser = build_parser()
    namespace = parser.parse_args(argv)
    output = stdout if stdout is not None else sys.stdout
    errors = stderr if stderr is not None else sys.stderr
    context = CommandContext(
        base_url=_normalized_base_url(namespace.base_url),
        json_output=bool(namespace.json_output),
        timeout=max(1.0, float(namespace.timeout)),
        stdout=output,
        stderr=errors,
        transport=transport if transport is not None else default_transport,
    )
    client = HermesHttpClient(context)
    try:
        result = _dispatch(namespace, context, client)
    except (CliRequestError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=errors)
        return 1
    return result


def main() -> int:
    """Console script entry point.

    Args:
        None.

    Returns:
        Process-style exit code.
    """
    exit_code = run()
    return exit_code


# Dynamic attribute justified: argparse.Namespace is the standard argparse boundary object.
def _dispatch(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    handler = namespace.handler
    if handler == "health":
        return _handle_health(context, client)
    if handler == "skills_list":
        return _handle_skills_list(namespace, context, client)
    if handler == "skills_get":
        return _handle_skills_get(namespace, context, client)
    if handler == "skills_create":
        return _handle_skills_create(namespace, context, client)
    if handler == "skills_delete":
        return _handle_skills_delete(namespace, context, client)
    if handler == "prompts_list":
        return _handle_prompts_list(namespace, context, client)
    if handler == "prompts_get":
        return _handle_prompts_get(namespace, context, client)
    if handler == "prompts_create":
        return _handle_prompts_create(namespace, context, client)
    if handler == "prompts_use":
        return _handle_prompts_use(namespace, context, client)
    if handler == "folders_list":
        return _handle_folders_list(namespace, context, client)
    if handler == "folders_create":
        return _handle_folders_create(namespace, context, client)
    if handler == "folders_delete":
        return _handle_folders_delete(namespace, context, client)
    if handler == "library_list":
        return _handle_library_list(namespace, context, client)
    if handler == "library_search":
        return _handle_library_search(namespace, context, client)
    if handler == "minio_scan":
        return _handle_minio_scan(namespace, context, client)
    if handler == "minio_import":
        return _handle_minio_import(namespace, context, client)
    raise ValueError(f"unknown command handler: {handler}")


def _handle_health(context: CommandContext, client: HermesHttpClient) -> int:
    payload = client.get("/health/live")
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        print("Hermes backend is reachable", file=context.stdout)
    return 0


def _handle_skills_list(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    limit = _bounded_limit(namespace.limit, default=20)
    offset = max(0, int(namespace.offset))
    payload = client.get(f"/skills?limit={limit}&offset={offset}")
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        _print_item_table(payload, context.stdout)
    return 0


def _handle_skills_get(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    item_id = str(namespace.item_id)
    payload = client.get(f"/skills/{_quote_path(item_id)}")
    _print_json(payload, context.stdout)
    return 0


def _handle_skills_create(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    body = _skill_create_payload(namespace)
    payload = client.post("/skills", body)
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        title = _text_field(payload, "title")
        item_id = _text_field(payload, "id")
        print(f"created skill {item_id}: {title}", file=context.stdout)
    return 0


def _handle_skills_delete(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    item_id = str(namespace.item_id)
    client.delete(f"/skills/{_quote_path(item_id)}")
    if context.json_output:
        _print_json({"deleted": item_id}, context.stdout)
    else:
        print(f"deleted skill {item_id}", file=context.stdout)
    return 0


def _handle_prompts_list(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    limit = _bounded_limit(namespace.limit, default=20)
    offset = max(0, int(namespace.offset))
    payload = client.get(f"/prompts?limit={limit}&offset={offset}")
    rows = _json_list(payload)
    if namespace.kind:
        rows = [
            row
            for row in rows
            if _detail_text(row, "prompt_kind") == str(namespace.kind)
        ]
    if namespace.tag:
        rows = [row for row in rows if str(namespace.tag) in _list_field(row, "tags")]
    output_payload: JSONValue = rows
    if context.json_output:
        _print_json(output_payload, context.stdout)
    else:
        _print_prompt_table(output_payload, context.stdout)
    return 0


def _handle_prompts_get(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    item_id = str(namespace.item_id)
    payload = client.get(f"/prompts/{_quote_path(item_id)}")
    _print_json(payload, context.stdout)
    return 0


def _handle_prompts_create(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    body = _prompt_create_payload(namespace)
    payload = client.post("/prompts", body)
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        title = _text_field(payload, "title")
        item_id = _text_field(payload, "id")
        print(f"created prompt {item_id}: {title}", file=context.stdout)
    return 0


def _handle_prompts_use(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    item_id = str(namespace.item_id)
    payload = client.get(f"/prompts/{_quote_path(item_id)}")
    usage_payload: JSONObject = {
        "item_id": item_id,
        "item_type": "PROMPT",
        "agent_name": str(namespace.actor_name),
        "librarian_provider": _optional_text(namespace.actor_id),
        "query": None,
        "selection_source": "DIRECT_LINK",
        "success": True,
        "feedback": None,
    }
    usage = client.post("/usage", usage_payload)
    if context.json_output:
        _print_json({"prompt": payload, "usage": usage}, context.stdout)
    else:
        print(_text_field(payload, "content"), file=context.stdout)
    return 0


def _handle_folders_list(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    path = "/categories/tree" if bool(namespace.tree) else "/categories"
    payload = client.get(path)
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        _print_folder_table(payload, context.stdout, tree=bool(namespace.tree))
    return 0


def _handle_folders_create(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    body: JSONObject = {
        "name": str(namespace.name),
        "parent_id": _optional_text(namespace.parent_id),
    }
    payload = client.post("/categories", body)
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        folder_id = _text_field(payload, "id")
        name = _text_field(payload, "name")
        print(f"created folder {folder_id}: {name}", file=context.stdout)
    return 0


def _handle_folders_delete(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    folder_id = str(namespace.folder_id)
    client.delete(f"/categories/{_quote_path(folder_id)}")
    if context.json_output:
        _print_json({"deleted": folder_id}, context.stdout)
    else:
        print(f"deleted folder {folder_id}", file=context.stdout)
    return 0


def _handle_library_list(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    params = [
        ("limit", str(_bounded_limit(namespace.limit, default=20))),
        ("offset", str(max(0, int(namespace.offset)))),
    ]
    if namespace.type:
        params.append(("item_type", str(namespace.type)))
    if namespace.folder_id:
        params.append(("category_id", str(namespace.folder_id)))
    if namespace.query:
        params.append(("q", str(namespace.query)))
    query = urllib.parse.urlencode(params)
    payload = client.get(f"/items?{query}")
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        _print_item_table(
            payload, context.stdout, empty_message="No library items found."
        )
    return 0


def _handle_library_search(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    query = urllib.parse.urlencode({"q": str(namespace.query)})
    payload = client.get(f"/search?{query}")
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        _print_item_table(
            payload, context.stdout, empty_message="No matching items found."
        )
    return 0


def _handle_minio_scan(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    limit = _bounded_limit(namespace.limit, default=24)
    payload = client.get(f"/storage/minio/import-candidates?limit={limit}")
    if namespace.type:
        rows = [
            row
            for row in _json_list(payload)
            if _text_field(row, "item_type") == str(namespace.type)
        ]
        payload = rows
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        _print_candidate_table(payload, context.stdout)
    return 0


def _handle_minio_import(
    namespace: argparse.Namespace,
    context: CommandContext,
    client: HermesHttpClient,
) -> int:
    limit = _bounded_limit(namespace.limit, default=48)
    payload = client.post("/storage/minio/import", {"limit": limit})
    if context.json_output:
        _print_json(payload, context.stdout)
    else:
        imported = _text_field(payload, "imported_count")
        skipped = _text_field(payload, "skipped_count")
        print(
            f"MINIO sync complete: {imported} imported, {skipped} skipped",
            file=context.stdout,
        )
    return 0


def _skill_create_payload(namespace: argparse.Namespace) -> JSONObject:
    content = _skill_content(namespace.content, namespace.content_file)
    status = "ACTIVE" if bool(namespace.active) else "DRAFT"
    payload: JSONObject = {
        "title": str(namespace.title),
        "summary": _optional_text(namespace.summary),
        "content": content,
        "category_id": _optional_text(namespace.category_id),
        "tags": [str(tag) for tag in namespace.tag],
        "purpose": str(namespace.purpose),
        "input_schema": {},
        "output_schema": {},
        "usage_example": _optional_text(namespace.usage_example),
        "required_tools": [str(tool) for tool in namespace.tool],
        "risk_level": str(namespace.risk_level),
        "version": str(namespace.version),
        "created_by_name": str(namespace.created_by),
        "status": status,
    }
    return payload


def _skill_content(content: str | None, content_file: str | None) -> str:
    if content_file:
        if content_file == "-":
            loaded_content = sys.stdin.read()
        else:
            loaded_content = Path(content_file).read_text(encoding="utf-8")
    else:
        loaded_content = content or ""
    if not loaded_content.strip():
        raise ValueError("skill content is required via --content or --content-file")
    return loaded_content


def _prompt_create_payload(namespace: argparse.Namespace) -> JSONObject:
    content = _prompt_content(namespace.content, namespace.content_file)
    status = "ACTIVE" if bool(namespace.active) else "DRAFT"
    payload: JSONObject = {
        "title": str(namespace.title),
        "summary": _optional_text(namespace.summary),
        "content": content,
        "category_id": _optional_text(namespace.category_id),
        "tags": [str(tag) for tag in namespace.tag],
        "content_format": str(namespace.format),
        "prompt_kind": str(namespace.kind),
        "prompt_domain": str(namespace.domain),
        "prompt_task_type": str(namespace.task_type),
        "input_variables": [_prompt_variable_payload(raw) for raw in namespace.var],
        "output_format": _optional_text(namespace.output_format),
        "target_actor": _optional_text(namespace.target_actor),
        "target_model_family": _optional_text(namespace.target_model_family),
        "language": _optional_text(namespace.language),
        "related_item_ids": [str(item_id) for item_id in namespace.related_item_id],
        "version": str(namespace.version),
        "created_by_name": str(namespace.created_by),
        "created_by_type": str(namespace.created_by_type),
        "source_type": str(namespace.source_type),
        "status": status,
    }
    return payload


def _prompt_variable_payload(raw_value: str) -> JSONObject:
    name, _, rest = raw_value.partition(":")
    variable_name = name.strip()
    if not variable_name:
        raise ValueError("prompt variable name is required")
    parts = rest.split(":") if rest else []
    required = True
    description_parts: list[str] = []
    for part in parts:
        normalized = part.strip()
        if normalized == "required":
            required = True
        elif normalized == "optional":
            required = False
        elif normalized:
            description_parts.append(normalized)
    payload: JSONObject = {
        "name": variable_name,
        "required": required,
        "description": ":".join(description_parts) or None,
        "default_value": None,
        "example": None,
        "input_type": "text",
    }
    return payload


def _prompt_content(content: str | None, content_file: str | None) -> str:
    if content_file:
        if content_file == "-":
            loaded_content = sys.stdin.read()
        else:
            loaded_content = Path(content_file).read_text(encoding="utf-8")
    else:
        loaded_content = content or ""
    if not loaded_content.strip():
        raise ValueError("prompt content is required via --content or --content-file")
    return loaded_content


def _normalized_base_url(value: str) -> str:
    normalized = value.rstrip("/")
    return normalized or DEFAULT_API_URL


def _join_url(base_url: str, path: str) -> str:
    joined = f"{base_url}{path}"
    return joined


def _quote_path(value: str) -> str:
    quoted = urllib.parse.quote(value, safe="")
    return quoted


def _bounded_limit(value: int, default: int) -> int:
    candidate = int(value) if value > 0 else default
    bounded = min(max(candidate, 1), 1000)
    return bounded


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _json_bytes(payload: JSONValue) -> bytes:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return encoded


def _decode_json(body: bytes) -> JSONValue:
    if not body:
        return None
    decoded = json.loads(body.decode("utf-8"))
    payload = cast(JSONValue, decoded)
    return payload


def _error_message(body: bytes) -> str:
    try:
        payload = _decode_json(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body.decode("utf-8", errors="replace") or "request failed"
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message")
        if isinstance(detail, str):
            return detail
    return "request failed"


def _print_json(payload: JSONValue, stdout: TextIO) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stdout)


def _print_item_table(
    payload: JSONValue,
    stdout: TextIO,
    empty_message: str = "No skills found.",
) -> None:
    rows = _json_list(payload)
    if not rows:
        print(empty_message, file=stdout)
        return
    print("ID\tTYPE\tTITLE", file=stdout)
    for item in rows:
        item_id = _text_field(item, "id")
        item_type = _text_field(item, "item_type")
        title = _text_field(item, "title")
        print(f"{item_id}\t{item_type}\t{title}", file=stdout)


def _print_prompt_table(
    payload: JSONValue,
    stdout: TextIO,
    empty_message: str = "No prompts found.",
) -> None:
    rows = _json_list(payload)
    if not rows:
        print(empty_message, file=stdout)
        return
    print("ID\tTYPE\tKIND\tTITLE", file=stdout)
    for item in rows:
        item_id = _text_field(item, "id")
        item_type = _text_field(item, "item_type")
        kind = _detail_text(item, "prompt_kind")
        title = _text_field(item, "title")
        print(f"{item_id}\t{item_type}\t{kind}\t{title}", file=stdout)


def _detail_text(payload: JSONValue, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    details = payload.get("details")
    if not isinstance(details, dict):
        return ""
    value = details.get(key)
    if isinstance(value, str):
        return value
    return ""


def _list_field(payload: JSONValue, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _print_folder_table(payload: JSONValue, stdout: TextIO, tree: bool) -> None:
    rows = _json_list(payload)
    if not rows:
        print("No folders found.", file=stdout)
        return
    print("ID\tPARENT\tNAME", file=stdout)
    if tree:
        for item in rows:
            _print_folder_tree_row(item, stdout, depth=0)
    else:
        for item in rows:
            folder_id = _text_field(item, "id")
            parent_id = _text_field(item, "parent_id") or "-"
            name = _text_field(item, "name")
            print(f"{folder_id}\t{parent_id}\t{name}", file=stdout)


def _print_folder_tree_row(item: JSONObject, stdout: TextIO, depth: int) -> None:
    folder_id = _text_field(item, "id")
    parent_id = _text_field(item, "parent_id") or "-"
    name = _text_field(item, "name")
    indent = "  " * depth
    print(f"{folder_id}\t{parent_id}\t{indent}{name}", file=stdout)
    children = item.get("children")
    if not isinstance(children, list):
        return
    for child in children:
        if isinstance(child, dict):
            _print_folder_tree_row(child, stdout, depth + 1)


def _print_candidate_table(payload: JSONValue, stdout: TextIO) -> None:
    rows = _json_list(payload)
    if not rows:
        print("No MINIO import candidates found.", file=stdout)
        return
    print("ID\tTYPE\tCONFIDENCE\tOBJECT", file=stdout)
    for item in rows:
        item_id = _text_field(item, "id")
        item_type = _text_field(item, "item_type")
        confidence = _text_field(item, "confidence")
        object_key = _text_field(item, "object_key")
        print(f"{item_id}\t{item_type}\t{confidence}\t{object_key}", file=stdout)


def _json_list(payload: JSONValue) -> list[JSONObject]:
    if not isinstance(payload, list):
        return []
    rows = [item for item in payload if isinstance(item, dict)]
    return rows


def _text_field(payload: JSONValue, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return str(value)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
