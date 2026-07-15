.PHONY: install-local format_check type_checking cli_smoke guardrails test ci

install-local:
	uv sync --no-editable --reinstall-package alexandria-hermes

format_check:
	uv run --no-editable ruff format --check .
	uv run --no-editable ruff check .

type_checking:
	uv run --no-editable pyrefly check

cli_smoke: install-local
	uv run --no-editable alexandria-hermes --help >/dev/null
	uv run --no-editable alex-hermes --help >/dev/null

guardrails:
	uv run --no-editable pytest -q tests/shared/guardrails

test:
	uv run --no-editable pytest -q

ci: format_check type_checking cli_smoke guardrails test
