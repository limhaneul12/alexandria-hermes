"""launchd service-file renderer for the local backend daemon."""

from __future__ import annotations

from xml.sax.saxutils import escape

from app.cli_support.daemon.service_contracts import ServiceDefinition


def render_launchd_plist(service: ServiceDefinition) -> str:
    """Render a launchd plist for `alexandria-hermes serve`.

    Args:
        service: Service definition with paths and network binding.

    Returns:
        XML plist text.
    """
    args = [
        service.cli_command,
        "serve",
        "--env-file",
        str(service.env_file),
        "--host",
        service.host,
        "--port",
        str(service.port),
    ]
    program_arguments = "\n".join(
        f"        <string>{escape(argument)}</string>" for argument in args
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<!-- alexandria-hermes serve --env-file {escape(str(service.env_file))} --host {escape(service.host)} --port {service.port} -->
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.alexandria-hermes.backend</string>
    <key>ProgramArguments</key>
    <array>
{program_arguments}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{escape(str(service.log_path))}</string>
    <key>StandardErrorPath</key>
    <string>{escape(str(service.log_path))}</string>
</dict>
</plist>
"""
