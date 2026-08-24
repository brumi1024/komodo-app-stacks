# AGENTS.md

Start with `README.md` for the high-level picture.
This file captures the non-obvious rules that aren't spelled out there.

## Related repositories

- `brumi1024/homelab-infra`: Ansible bootstrap of the hosts, Komodo Core and Periphery, and the live-state notes.
  Host and inventory questions go there.
- `brumi1024/komodo-resource-syncs`: the sync that pulls this repo into Komodo.
  Add or rename a sync there, not here.
- `brumi1024/deploy-komodo-op`: the komodo-op stack that turns 1Password items into the `[[OP__KOMODO__*]]` variables used here.

## Reusable procedures

- Use `$komodo-stack-lifecycle` for adding, removing, or auditing a stack across the four Komodo repositories.
- Use `$renovate-pr-triage` for read-only risk classification of Renovate pull requests before merge.

## Secrets

- All secret values come from 1Password via `komodo-op`.
  Reference them as `[[OP__KOMODO__<STACK>__<NAME>]]` inside the `environment` block of `stack.toml`.
- **Never** commit a secret value, even temporarily.
  If a secret isn't in 1Password yet, tell the user - don't invent a placeholder.
- Non-secret shared vars use short names: `[[TZ]]`, `[[CONFIG_DIR]]`, `[[DOMAIN]]`, etc.

## Ports

- Host port mappings are centralised in `common-vars.toml` as `PORT_*` variables.
  Add a new entry there before using it in a compose file; don't hardcode host ports.
- Check for collisions before picking a default (e.g. grep `common-vars.toml`).

## Adding a new stack

1. Create `services/<name>/docker-compose.yaml` and `services/<name>/stack.toml`.
2. Use the `paperless` or `tautulli` stack as a template.
3. Every service block should set `container_name` and `restart`.
   Container logging policy is configured once on each Docker daemon rather than repeated in stack files.
4. Persistent data goes under `${CONFIG_DIR}/<stack>/...`.
   NFS volumes use `addr=${NAS_IP},rw,vers=4.1` (see `immich`, `paperless`).
5. User-facing services get `homepage.*` labels; internal-only sidecars do not.

## Multi-instance stacks

Services with multiple deployments (AutoKuma, Caddy, Nebula Sync, proxy, and Zigbee2MQTT) follow the base + override pattern:

- `services/<name>/docker-compose.yaml` - shared base
- `services/<name>/<instance>/docker-compose.yaml` - instance override when one is needed
- `services/<name>/<instance>/stack.toml` - Komodo resource referencing the base and override in `file_paths` order

## Deployment

This repo is GitOps.
Pushing to `main` triggers Komodo sync and auto-deploys stacks with `auto_update = true`.
Don't `docker compose up` manually on target hosts.

- Every stack must set a unique `env_file_path` relative to its `run_directory`.
- If a Compose service uses `env_file`, reference `${KOMODO_ENV_FILE:-.env}` and set `KOMODO_ENV_FILE` to the same path inside that stack's `environment` block.

### Config-file-only changes need a restart, not a deploy

Komodo's Deploy runs `docker compose up -d`, which does nothing when the Compose file itself is unchanged.
A change to a `config_files` entry - most often a Caddyfile - therefore leaves the old process running with its old configuration, while Komodo records the stack as deployed at the new commit.
The stack reads as current at the right hash while the running service is stale.

Neither Deploy nor Restart pulls the repository.
The linked repo is refreshed by the resource sync, which normally runs from the push webhook, so a restart issued straight after a push can apply the previous commit.

After changing a Caddyfile or any other `config_files` entry, run the `komodo-app-stacks` **sync** to pull, then **Restart** that stack to apply.
Deploy is a no-op here because the Compose file itself has not changed.

Mount the config *directory* rather than an individual file.
A `git pull` replaces files instead of editing them, so a single-file bind mount keeps resolving to the old, now-unlinked inode and a restart alone would not help.
Do not add a more-specific single-file mount in an instance override, because Compose retains it alongside the base directory mount.

The Home Caddy override currently has such a legacy single-file mount.
Treat it as an implementation issue to remove before relying on Restart alone for Home Caddyfile changes.
