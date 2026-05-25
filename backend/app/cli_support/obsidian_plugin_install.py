"""Local Obsidian plugin installation helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from app.shared.serialization.orjson_codec import dumps_pretty_json, loads_json
from app.shared.types.extra_types import JSONObject

PLUGIN_ID = "alexandria-librarian"


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianInstallLocalResult:
    """Result of a local Obsidian plugin install."""

    vault_path: str
    plugin_target: str
    plugin_install_mode: str
    plugin_installed: bool
    plugin_enabled: bool

    def to_payload(self) -> JSONObject:
        """Return JSON-compatible result payload.

        Returns:
            JSON-compatible install result.
        """
        return {
            "vault_path": self.vault_path,
            "plugin_target": self.plugin_target,
            "plugin_install_mode": self.plugin_install_mode,
            "plugin_installed": self.plugin_installed,
            "plugin_enabled": self.plugin_enabled,
        }


def install_local_obsidian_plugin(
    *,
    vault_path: str,
    install_mode: str,
    enable_plugin: bool,
) -> ObsidianInstallLocalResult:
    """Install the Alexandria Obsidian plugin into one local vault.

    Args:
        vault_path: Target Obsidian vault path.
        install_mode: Plugin install mode, either copy or symlink.
        enable_plugin: Whether to enable the plugin in community-plugins.json.

    Returns:
        Local install result summary.
    """
    vault = Path(vault_path).expanduser().resolve()
    plugin_source = _plugin_source_path()
    if install_mode not in {"copy", "symlink"}:
        raise ValueError("plugin install mode must be copy or symlink")
    if not plugin_source.exists():
        raise FileNotFoundError(f"Obsidian plugin source not found: {plugin_source}")
    plugin_root = vault / ".obsidian" / "plugins"
    target = plugin_root / PLUGIN_ID
    plugin_root.mkdir(parents=True, exist_ok=True)
    if install_mode == "symlink":
        _replace_with_symlink(target, plugin_source)
    else:
        _copy_plugin(plugin_source, target)
    if enable_plugin:
        _enable_plugin(vault)
    return ObsidianInstallLocalResult(
        vault_path=str(vault),
        plugin_target=str(target),
        plugin_install_mode=install_mode,
        plugin_installed=target.exists(),
        plugin_enabled=_plugin_enabled(vault),
    )


def _plugin_source_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "integrations" / "obsidian" / PLUGIN_ID


def _replace_with_symlink(target: Path, source: Path) -> None:
    if target.is_symlink() or target.exists():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.symlink_to(source, target_is_directory=True)


def _copy_plugin(source: Path, target: Path) -> None:
    if target.is_symlink():
        target.unlink()
    target.mkdir(parents=True, exist_ok=True)
    _remove_stale_plugin_files(target)
    for child in source.iterdir():
        if child.name == "data.json":
            continue
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(child, destination)


def _remove_stale_plugin_files(target: Path) -> None:
    for child in target.iterdir():
        if child.name == "data.json":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _enable_plugin(vault: Path) -> None:
    config_dir = vault / ".obsidian"
    config_dir.mkdir(parents=True, exist_ok=True)
    community_plugins_path = config_dir / "community-plugins.json"
    plugins = _community_plugins(community_plugins_path)
    if PLUGIN_ID not in plugins:
        plugins.append(PLUGIN_ID)
    community_plugins_path.write_bytes(dumps_pretty_json(plugins))
    app_path = config_dir / "app.json"
    app_payload = _json_object_from_file(app_path)
    app_payload["safeMode"] = False
    app_path.write_bytes(dumps_pretty_json(app_payload))


def _community_plugins(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = loads_json(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _json_object_from_file(path: Path) -> JSONObject:
    if not path.exists():
        return {}
    value = loads_json(path.read_text(encoding="utf-8"))
    return dict(value) if isinstance(value, dict) else {}


def _plugin_enabled(vault: Path) -> bool:
    return PLUGIN_ID in _community_plugins(
        vault / ".obsidian" / "community-plugins.json"
    )
