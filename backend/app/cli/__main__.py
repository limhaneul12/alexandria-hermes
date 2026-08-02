"""Package execution entrypoint for ``python -m app.cli``."""

from app.cli.main import main

raise SystemExit(main())
