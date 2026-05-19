# Security Policy

## Supported status

Alexandria-Hermes is an active MVP intended for local or otherwise access-controlled single-operator use.

## Security model

Alexandria-Hermes is **no-login, single-operator, local-first** software.

- There is no signup/login/session/RBAC system.
- Sensitive control-plane routes are protected by one operator key.
- Backend service config receives the key as `ALEXANDRIA_OPERATOR_API_KEY`.
- CLI/MCP/frontend server proxy clients send `ALEXANDRIA_OPERATOR_API_KEY` to the backend operator-key header.
- `ALEXANDRIA_API_TOKEN` is not an active product auth mechanism.

## Network exposure

Do not expose a default Alexandria-Hermes instance directly to the public internet.

Before exposing it outside localhost, put it behind an access boundary such as:

- VPN or private overlay network
- reverse proxy authentication
- firewall allowlist
- SSH tunnel
- private subnet

## Sensitive data

Alexandria-Hermes can store agent context, handoffs, decisions, prompts, skills, usage metadata, and optional provider configuration. Treat the local database and provider secret store as sensitive.

Do not store raw secrets in library/context content:

- API keys
- passwords
- OAuth access/refresh tokens
- private keys
- full unredacted conversation logs

Use placeholders such as `<operator-key>` or `[REDACTED]` in examples and reports.

## Reporting vulnerabilities

Until a public security contact is configured, please report security issues privately to the repository maintainer. Do not open public issues with exploit details or real secrets.

Include:

- affected version/commit
- reproduction steps
- expected vs actual behavior
- whether secrets or stored context may be exposed

## Local response checklist

If you suspect exposure:

1. Stop the backend/frontend processes.
2. Rotate the operator key and any provider credentials.
3. Inspect logs for accidental secret output.
4. Review stored context/library records for raw secrets.
5. Restore from a known-good backup if needed.
