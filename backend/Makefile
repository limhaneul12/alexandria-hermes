.PHONY: install-local format_check type_checking guardrails test ci

install-local:
	uv sync

format_check:
	uv run ruff format --check .
	uv run ruff check .

type_checking:
	uv run pyrefly check

guardrails:
	uv run pytest -q tests/shared/guardrails

test:
	uv run pytest -q

ci: format_check type_checking guardrails test
