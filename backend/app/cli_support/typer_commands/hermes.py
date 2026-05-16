"""Native Typer commands for Hermes integration operations."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import (
    HermesBundleCommand,
    HermesConfigureCommand,
    HermesDoctorCommand,
    HermesInstallCommand,
    HermesOnboardCommand,
    HermesPolicyCommand,
    HermesScanCommand,
    HermesSyncCommand,
)
from app.cli_support.handlers.hermes import (
    handle_hermes_configure,
    handle_hermes_doctor,
    handle_hermes_install,
    handle_hermes_install_mcp,
    handle_hermes_install_prompts,
    handle_hermes_onboard,
    handle_hermes_policy,
    handle_hermes_scan,
    handle_hermes_sync,
)
from app.cli_support.typer_commands.typer_runtime import run_local

hermes_app = typer.Typer(help="Install Alexandria-Hermes assets into Hermes")
policy_app = typer.Typer(help="Manage Hermes Alexandria usage policy")


def _bundle_command(
    hermes_home: str | None,
    api_url: str | None,
    api_token: str,
    dry_run: bool,
    overwrite: bool,
) -> HermesBundleCommand:
    return HermesBundleCommand(
        hermes_home=hermes_home,
        api_url=api_url,
        api_token=api_token,
        dry_run=dry_run,
        overwrite=overwrite,
        apply=True,
        restart_hint=False,
        print_first_prompt=False,
    )


@hermes_app.command("install")
def hermes_install(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    api_token: str = typer.Option(
        "",
        "--api-token",
        envvar="ALEXANDRIA_API_TOKEN",
    ),
    apply: bool = typer.Option(False, "--apply"),
    restart_hint: bool = typer.Option(False, "--restart-hint"),
    print_first_prompt: bool = typer.Option(False, "--print-first-prompt"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Install Hermes prompts and MCP config in one guided command.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.
        api_url: Optional Alexandria API URL.
        api_token: Optional Alexandria API token.
        apply: Whether to write files; omitted means preview.
        restart_hint: Whether to include session restart guidance.
        print_first_prompt: Whether to include the first Hermes prompt.
        overwrite: Whether to overwrite existing files.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesInstallCommand(
            hermes_home=hermes_home,
            api_url=api_url,
            api_token=api_token,
            dry_run=not apply,
            overwrite=overwrite,
            apply=apply,
            restart_hint=restart_hint,
            print_first_prompt=print_first_prompt or restart_hint,
        ),
        handle_hermes_install,
    )


@hermes_app.command("configure")
def hermes_configure(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    api_token: str = typer.Option(
        "",
        "--api-token",
        envvar="ALEXANDRIA_API_TOKEN",
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Save Hermes path config.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.
        api_url: Optional Alexandria API URL.
        api_token: Optional Alexandria API token.
        dry_run: Whether to preview changes only.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesConfigureCommand(
            hermes_home=hermes_home,
            api_url=api_url,
            api_token=api_token,
            dry_run=dry_run,
        ),
        handle_hermes_configure,
    )


@hermes_app.command("onboard")
def hermes_onboard(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    api_token: str = typer.Option(
        "",
        "--api-token",
        envvar="ALEXANDRIA_API_TOKEN",
    ),
    install_prompts: bool = typer.Option(False, "--install-prompts"),
    install_mcp: bool = typer.Option(False, "--install-mcp"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Install Hermes onboarding.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.
        api_url: Optional Alexandria API URL.
        api_token: Optional Alexandria API token.
        install_prompts: Whether to install prompt assets.
        install_mcp: Whether to install MCP config.
        overwrite: Whether to overwrite existing files.
        dry_run: Whether to preview changes only.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesOnboardCommand(
            hermes_home=hermes_home,
            api_url=api_url,
            api_token=api_token,
            dry_run=dry_run,
            overwrite=overwrite,
            install_prompts=install_prompts,
            install_mcp=install_mcp,
            apply=True,
            restart_hint=False,
            print_first_prompt=False,
        ),
        handle_hermes_onboard,
    )


@hermes_app.command("install-prompts")
def hermes_install_prompts(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    api_token: str = typer.Option(
        "",
        "--api-token",
        envvar="ALEXANDRIA_API_TOKEN",
    ),
    overwrite: bool = typer.Option(False, "--overwrite"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Install Alexandria prompt and skill assets.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.
        api_url: Optional Alexandria API URL.
        api_token: Optional Alexandria API token.
        overwrite: Whether to overwrite existing files.
        dry_run: Whether to preview changes only.

    Returns:
        None.
    """
    run_local(
        ctx,
        _bundle_command(
            hermes_home=hermes_home,
            api_url=api_url,
            api_token=api_token,
            dry_run=dry_run,
            overwrite=overwrite,
        ),
        handle_hermes_install_prompts,
    )


@hermes_app.command("install-mcp")
def hermes_install_mcp(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    api_token: str = typer.Option(
        "",
        "--api-token",
        envvar="ALEXANDRIA_API_TOKEN",
    ),
    overwrite: bool = typer.Option(False, "--overwrite"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Install Alexandria MCP config snippet.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.
        api_url: Optional Alexandria API URL.
        api_token: Optional Alexandria API token.
        overwrite: Whether to overwrite existing files.
        dry_run: Whether to preview changes only.

    Returns:
        None.
    """
    run_local(
        ctx,
        _bundle_command(
            hermes_home=hermes_home,
            api_url=api_url,
            api_token=api_token,
            dry_run=dry_run,
            overwrite=overwrite,
        ),
        handle_hermes_install_mcp,
    )


@hermes_app.command("doctor")
def hermes_doctor(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    api_token: str = typer.Option(
        "",
        "--api-token",
        envvar="ALEXANDRIA_API_TOKEN",
    ),
    require_home: bool = typer.Option(False, "--require-home"),
    deep: bool = typer.Option(False, "--deep"),
) -> None:
    """Check Hermes integration.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.
        api_url: Optional Alexandria API URL.
        api_token: Optional Alexandria API token.
        require_home: Whether missing Hermes home should fail.
        deep: Whether to run deep readiness diagnostics.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesDoctorCommand(
            hermes_home=hermes_home,
            api_url=api_url,
            api_token=api_token,
            require_home=require_home,
            deep=deep,
        ),
        handle_hermes_doctor,
    )


@policy_app.command("status")
def hermes_policy_status(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
) -> None:
    """Show whether Hermes should use Alexandria-Hermes.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesPolicyCommand(hermes_home=hermes_home, enabled=None),
        handle_hermes_policy,
    )


@policy_app.command("enable")
def hermes_policy_enable(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
) -> None:
    """Enable Hermes Alexandria-Hermes usage.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesPolicyCommand(hermes_home=hermes_home, enabled=True),
        handle_hermes_policy,
    )


@policy_app.command("disable")
def hermes_policy_disable(
    ctx: typer.Context,
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
) -> None:
    """Disable Hermes Alexandria-Hermes usage.

    Args:
        ctx: Typer context.
        hermes_home: Optional Hermes home path.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesPolicyCommand(hermes_home=hermes_home, enabled=False),
        handle_hermes_policy,
    )


hermes_app.add_typer(policy_app, name="policy")


@hermes_app.command("scan")
def hermes_scan(
    ctx: typer.Context,
    path: str | None = typer.Argument(None),
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
) -> None:
    """Scan Hermes Alexandria assets.

    Args:
        ctx: Typer context.
        path: Optional path to scan.
        hermes_home: Optional Hermes home path.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesScanCommand(path=path, hermes_home=hermes_home),
        handle_hermes_scan,
    )


@hermes_app.command("sync")
def hermes_sync(
    ctx: typer.Context,
    path: str | None = typer.Argument(None),
    hermes_home: str | None = typer.Option(None, "--hermes-home"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Plan or install Hermes assets.

    Args:
        ctx: Typer context.
        path: Optional source path.
        hermes_home: Optional Hermes home path.
        dry_run: Whether to preview changes only.
        overwrite: Whether to overwrite existing files.

    Returns:
        None.
    """
    run_local(
        ctx,
        HermesSyncCommand(
            path=path,
            hermes_home=hermes_home,
            api_url=None,
            api_token="",
            dry_run=dry_run,
            overwrite=overwrite,
            apply=True,
            restart_hint=False,
            print_first_prompt=False,
        ),
        handle_hermes_sync,
    )
