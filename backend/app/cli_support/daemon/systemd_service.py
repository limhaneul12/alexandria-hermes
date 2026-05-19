"""systemd service-file renderer for the local backend daemon."""

from __future__ import annotations

import shlex

from app.cli_support.daemon.service_contracts import ServiceDefinition


def render_systemd_unit(service: ServiceDefinition) -> str:
    """Render a systemd user unit for `alexandria-hermes serve`.

    Args:
        service: Service definition with paths and network binding.

    Returns:
        systemd unit text.
    """
    exec_start = " ".join(
        [
            shlex.quote(service.cli_command),
            "serve",
            "--env-file",
            shlex.quote(str(service.env_file)),
            "--host",
            shlex.quote(service.host),
            "--port",
            str(service.port),
        ]
    )
    return f"""[Unit]
Description=Alexandria-Hermes backend SQLite daemon
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
StandardOutput=append:{service.log_path}
StandardError=append:{service.log_path}

[Install]
WantedBy=default.target
"""
