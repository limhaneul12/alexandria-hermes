from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


CONSOLE_SCRIPT = Path(sys.executable).with_name("alexandria-hermes")


def test_console_entrypoint_imports_app_from_outside_project_root(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "-c", "import app.cli; print(app.cli.main.__name__)"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "main"


def test_installed_console_script_shows_help_from_outside_project_root(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [str(CONSOLE_SCRIPT), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Alexandria-Hermes command line client" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
