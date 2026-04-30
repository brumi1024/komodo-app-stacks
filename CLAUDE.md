# CLAUDE.md

Start with `README.md` for the high-level picture. This file captures the non-obvious
rules that aren't spelled out there.

## Secrets

- All secret values come from 1Password via `komodo-op`. Reference them as
  `[[OP__KOMODO__<STACK>__<NAME>]]` inside the `environment` block of `stack.toml`.
- **Never** commit a secret value, even temporarily. If a secret isn't in 1Password yet,
  tell the user — don't invent a placeholder.
- Non-secret shared vars use short names: `[[TZ]]`, `[[CONFIG_DIR]]`, `[[DOMAIN]]`, etc.

## Ports

- Host port mappings are centralised in `common-vars.toml` as `PORT_*` variables.
  Add a new entry there before using it in a compose file; don't hardcode host ports.
- Check for collisions before picking a default (e.g. grep `common-vars.toml`).

## Adding a new stack

1. Create `services/<name>/docker-compose.yaml` and `services/<name>/stack.toml`.
2. Use the `paperless` or `tautulli` stack as a template.
3. Every service block should set: `container_name`, `restart`, and
   `logging.driver: ${LOGGING_DRIVER:-local}`.
4. Persistent data goes under `${CONFIG_DIR}/<stack>/...`. NFS volumes use
   `addr=${NAS_IP},rw,vers=4.1` (see `immich`, `paperless`).
5. User-facing services get `homepage.*` labels; internal-only sidecars do not.

## Multi-instance stacks

Services with multiple deployments (caddy, nebula-sync, zigbee2mqtt) follow the
base + override pattern:
- `services/<name>/docker-compose.yaml` — shared base
- `services/<name>/<instance>/docker-compose.yaml` — instance overrides
- `services/<name>-<instance>/stack.toml` references both in `file_paths` order

## Deployment

This repo is GitOps. Pushing to `main` triggers Komodo sync and auto-deploys stacks
with `auto_update = true`. Don't `docker compose up` manually on target hosts.
