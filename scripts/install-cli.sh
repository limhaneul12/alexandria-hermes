#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
INSTALL_DIR=${HERMES_CLI_INSTALL_DIR:-"$HOME/.local/bin"}

mkdir -p "$INSTALL_DIR"
ln -sf "$REPO_ROOT/bin/alexandria-hermes" "$INSTALL_DIR/alexandria-hermes"
ln -sf "$REPO_ROOT/bin/alex-hermes" "$INSTALL_DIR/alex-hermes"

printf 'Installed alexandria-hermes CLI links in %s\n' "$INSTALL_DIR"
printf 'If the command is not found, add this to your shell profile:\n'
printf '  export PATH="%s:$PATH"\n' "$INSTALL_DIR"
