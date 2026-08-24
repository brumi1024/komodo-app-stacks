# Homelab Komodo Stacks

This repository is the declarative source for application stacks managed by Komodo.

## Service model

The VPS is the public entry point and runs Caddy, Komodo Core, Pocket ID, Tinyauth, Uptime Kuma, AutoKuma, ntfy, Homepage, Beszel, and CrowdSec.
Caddy is the only VPS application that publishes public HTTP ports.
VPS-hosted applications communicate over the private `vps-ingress` Docker network, so their startup does not depend on a Tailscale address being present.

Pocket ID provides passkey-backed OIDC identity.
Applications with native OIDC support connect to Pocket ID directly, while Tinyauth provides Caddy forward authentication for browser-facing applications that do not support OIDC themselves.

One AutoKuma instance on the VPS reconciles all Uptime Kuma monitors.
It reads local container labels over the private `monitoring-control` network and remote labels through read-only Docker socket proxies over Tailscale.
The remote proxy ports must be protected by the host firewall so only the VPS can reach them.

Remote applications continue to use full MagicDNS names when traffic crosses hosts.
The VPS is the public edge for every site and forwards `*.home` and `*.seq` to that site's Caddy over Tailscale, preserving the original `Host` header.
Routing, authentication, and application-specific behaviour stay on the site Caddy rather than being duplicated on the VPS.

## Repository layout

Each `services/*/stack.toml` file declares a Komodo stack.
Most stacks use one Compose file, while repeated services use a shared base plus a site-specific override.
Every stack sets a unique `env_file_path` so concurrent automatic deployments cannot overwrite another stack's rendered environment.
Compose services that import the rendered file use `KOMODO_ENV_FILE`, with `.env` retained only as a local-development fallback.

```text
services/
  autokuma/       Central monitor reconciliation
  caddy/          Shared reverse-proxy base and site overrides
  pocket-id/      Passkey-backed OIDC identity provider
  proxy/          Read-only Docker API proxies
  monitoring/     Beszel server and VPS agent
  tinyauth/       Forward authentication backed by Pocket ID
  */stack.toml    Single-instance Komodo resource declarations
  */*/stack.toml  Site-specific Komodo resource declarations
scripts/
  validate_stacks.py
```

## Validation

Run the same validation used by CI before committing:

```bash
python3 scripts/validate_stacks.py
```

The validator parses every TOML resource, verifies referenced files, renders every Compose combination without resolving secrets, and rejects hard-coded Tailscale host addresses.

## Change workflow

1. Change the Compose and `stack.toml` files together.
2. Run `python3 scripts/validate_stacks.py`.
3. Review stateful-service release notes and backup requirements.
4. Commit the smallest coherent change.
5. Push only when the change is ready for Komodo resource synchronization.
6. Confirm health checks and external monitoring before removing the previous deployment.

Resource sync does not automatically make a stateful migration safe.
Database backups, data-directory moves, and control-plane relocation must use an explicit migration runbook with a tested rollback path.

The repository-owned `$renovate-pr-triage` skill under `.agents/skills/` provides read-only dependency pull-request risk classification.

## Adding a stack

Use an existing nearby service as the template.
Every long-running container should have an explicit restart policy.
Logging policy is owned by the Docker daemon rather than repeated in every stack.
Use named volumes or host paths under `CONFIG_DIR` for persistent state.
Prefer private Docker networking for same-host traffic and full MagicDNS names for cross-host traffic.
Add an unauthenticated health endpoint label when the application provides one.
