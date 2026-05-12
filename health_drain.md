# Backend Cleanup Report

## What Changed

- Removed the old `/health` compatibility route from `backend/app/main.py`.
- Kept only:
  - `/`
  - `/health/live`
  - `/health/ready`
  - `/health/heartbeat`

- Removed package-level export files under `backend/app` that were only used for re-export:
  - `app/__init__.py`
  - `app/platform/__init__.py`
  - `app/platform/config/__init__.py`
  - `app/platform/lifecycle/__init__.py`
  - `app/platform/logging/__init__.py`
  - `app/platform/logging/formatter/__init__.py`
  - `app/platform/middleware/__init__.py`
  - `app/platform/schemas/__init__.py`
  - `app/shared/__init__.py`
  - `app/shared/guardrails/__init__.py`
  - `app/shared/serialization/__init__.py`
  - `app/shared/types/__init__.py`
  - `app/shared/util/__init__.py`

- Removed compatibility wrapper modules that were no longer needed:
  - `backend/app/platform/config/common.py`
  - `backend/app/platform/logging/context/http_request.py`
  - `backend/app/platform/logging/context/log_record_extras.py`
  - `backend/app/platform/logging/context/` directory

- Updated imports to reference concrete modules directly.
  - Example: `from app.platform.config.app_config import AppConfig`
  - Example: `from app.platform.lifecycle.state import LifecycleState`
  - Example: `from app.platform.logging.formatter.config import configure_logging`
  - Example: `from app.platform.middleware.request_logging import install_request_logging_middleware`
  - Example: `from app.shared.serialization.model_codec import dumps_model, model_to_dict`
  - Example: `from app.shared.serialization.orjson_codec import dumps_json`

## Verification

- `cd backend && uv run ruff check .`
- `cd backend && uv run pyrefly check`
- `cd backend && uv run pytest -q`

All checks passed (`4 passed`).
