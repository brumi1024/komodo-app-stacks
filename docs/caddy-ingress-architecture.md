# Caddy multi-site ingress architecture

## Goals

The ingress design prefers a direct client-to-site path whenever the destination site has a usable public address family.
The VPS provides the missing address family and failure-path ingress, but it is not the preferred bulk-data path.
Tailscale is the private transport between Caddy edges and site services, and it should normally establish direct peer-to-peer UDP paths rather than use DERP.

## Site capabilities

| Site | Native public ingress | Public fallback | Tailnet path |
| --- | --- | --- | --- |
| VPS | IPv4 and IPv6 | Not required | Direct peer path to every site |
| Home | IPv4 on the primary WAN, used by direct Tailscale paths | Dual-stack VPS for public DNS | `docker` |
| Kalász | IPv4 | VPS for IPv6 and until a site-local Caddy edge is available | `homeassistant-kalasz` |
| Sequoia | IPv6 | VPS for IPv4-only clients | `docker-seq` |

## Routing matrix

Public DNS owns the first hop.
Caddy cannot make a browser retry a different edge when the DNS answer itself is unreachable.

| Name family | A record | AAAA record | Expected path |
| --- | --- | --- | --- |
| VPS services | VPS IPv4 | VPS IPv6 | Client to VPS |
| `*.home` | VPS IPv4 | VPS IPv6 | All clients use VPS to Home Caddy over Tailscale until Technitium split DNS is enabled; Tailnet clients then connect directly |
| `*.kalasz` | VPS IPv4 until a Kalász Caddy edge is deployed | VPS IPv6 | VPS to Kalász over Tailscale |
| `*.seq` | VPS IPv4 | Sequoia IPv6 | Public IPv4 goes through VPS and public IPv6 goes directly to Sequoia; Tailnet clients connect directly after Technitium split DNS is enabled |

The VPS Caddy forwards `*.home` and `*.seq` to the corresponding site Caddy over Tailscale.
It preserves the original HTTP `Host` header while using each site's Home Assistant certificate as a stable upstream TLS identity.
The stable TLS identity lets Caddy reuse upstream connections across fallback hostnames instead of creating transports from request placeholders.
This keeps routing, authentication, and application-specific behavior on the site Caddy instead of duplicating every route on the VPS.

The site Caddy instances trust Tailnet proxy addresses for forwarded-client parsing and use Caddy's `client_ip` matcher for Tailnet authentication bypass.
A public request forwarded by the VPS therefore retains its public client address and does not receive the Tailnet bypass merely because the final proxy hop came from a Tailscale address.

## Dynamic DNS ownership

Each `dynamic_dns` app must manage records that point to the machine running that Caddy instance.
The module has one effective app configuration with one IP-source set, so repeated `dynamic_dns` blocks are not a way to express per-domain address-family policies.

The VPS manages `@`, `*`, `*.home`, and `*.kalasz` with both IPv4 and IPv6.
Home does not manage public service-address records because its canonical public path must remain reachable during CGNAT backup operation.
Sequoia manages `seq`, `seq-origin-v6`, and `*.seq` with IPv6 only.

The remaining asymmetric fallback record must be managed outside these per-edge Dynamic DNS policies:

- `A *.seq` points to the stable VPS IPv4 address.

This two-plane design deliberately avoids health-aware Home DNS steering.
The public Home names remain on the stable dual-stack VPS, while the planned Tailscale split DNS will give managed clients the direct site path.
Home WAN failover therefore changes the Tailscale underlay path without changing the application hostname or public DNS.

## Planned bulk-data policy

After Technitium split DNS is enabled, Tailnet clients should use it for the site suffixes so they connect to the site Caddy directly:

- `*.home.<domain>` resolves through MagicDNS to the Tailscale address of `docker`.
- `*.seq.<domain>` resolves through MagicDNS to the Tailscale address of `docker-seq`.

This will keep Immich, Plex, NAS, and other large transfers off the VPS for managed clients even though canonical public Home DNS is intentionally anchored on the VPS.
Public clients without Tailscale can still use the VPS fallback where reachability is more important than avoiding transit.

This private DNS capability is intentionally deferred until the planned Technitium deployment.
Do not deploy a temporary CoreDNS authority for these zones.
Until Technitium is ready, Tailnet clients use the same public VPS fallback path as other clients.

### TODO: implement with Technitium

- [ ] Deploy at least two healthy Technitium resolver nodes and leave Technitium DHCP disabled so UniFi retains DHCP, VLAN, and reservation ownership.
- [ ] Create private authoritative views for `home.<domain>` and `seq.<domain>` that resolve wildcard application names to the corresponding site Caddy identities, `docker.<tailnet>` and `docker-seq.<tailnet>`.
- [ ] Ensure the Technitium nodes can resolve the Tailscale MagicDNS targets without storing transient Tailscale addresses in the application zones.
- [ ] Listen on the intended LAN and Tailscale interfaces and restrict UDP and TCP port 53 to authorized LAN and Tailnet clients.
- [ ] Configure both healthy resolver addresses as Tailscale restricted nameservers for `home.<domain>` and `seq.<domain>` rather than as global nameservers.
- [ ] Confirm clients using a Tailscale exit node retain both restricted DNS routes.
- [ ] Verify both resolver nodes return direct site-Caddy answers to Tailnet clients while public resolvers continue returning the VPS and direct-site records described above.
- [ ] Verify resolver-node loss does not remove access to either private zone and document the Technitium primary-promotion procedure.

Kalász needs a site-local Caddy or equivalent port-443 edge before its public IPv4 can become a direct HTTPS path.
The observed Kalász public IPv4 does not currently accept HTTPS, so its existing VPS-to-Tailscale route remains the reliable path.

## Deployment and change procedure

The multi-site ingress topology is deployed.
The repository currently builds Caddy `2.11.4` with the custom modules pinned in `services/caddy/caddy-build/Dockerfile`.

The asymmetric Cloudflare fallback record remains an external prerequisite and must be preserved:

```text
A *.seq.<domain> -> VPS IPv4
```

This record is managed outside Caddy because the VPS `dynamic_dns` app cannot publish an IPv4-only Sequoia record while also publishing dual-stack records for its other names.

For Caddyfile-only changes, first run the `komodo-app-stacks` resource sync so the linked repository is current, then Restart the affected Caddy stack.
Deploy does not apply a config-file-only change when the Compose definition is unchanged.
See the deployment guidance in the repository `AGENTS.md` for the underlying bind-mount behavior.

For topology or Caddy build changes, update and verify the site edges before the VPS fallback edge.
Confirm Home and Sequoia direct routes and Tailscale HTTPS listeners before changing VPS fallback routing.

The VPS Dynamic DNS policy maintains both address families for `*.home` and `*.kalasz`.
Allow for the configured DNS TTL before treating a negative cached A answer as a failed deployment.

After a change, verify that a non-Tailnet client receives the VPS addresses for Home and Kalász, receives the address-family-specific direct and fallback records for Sequoia, and can reach every intended public service.

Implement the Technitium TODO as a separate DNS-platform change after the public ingress path is healthy.
The public Caddy deployment does not depend on private split DNS.

## Operational verification

Validate every Caddyfile with the same Caddy build used by the target stack:

```bash
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile --pretty
```

The adapted VPS JSON must contain one `dynamic_dns` app with both `ipv4` and `ipv6` enabled.

Check public answers from an external resolver:

```bash
dig @1.1.1.1 service.home.example.com A +short
dig @1.1.1.1 service.home.example.com AAAA +short
dig @1.1.1.1 service.seq.example.com A +short
dig @1.1.1.1 service.seq.example.com AAAA +short
```

Test from IPv4-only, IPv6-capable, and Tailnet clients:

```bash
curl -4 -I https://service.example.com
curl -6 -I https://service.example.com
tailscale ping docker
tailscale ping docker-seq
tailscale ping homeassistant-kalasz
```

For a large-file service, confirm the selected peer with `tailscale status` or `tailscale ping` during a representative transfer.
Before Technitium split DNS is enabled, the expected application path is through the public VPS fallback even when the Tailscale peer path beneath that proxy hop is direct.
After the Technitium TODO is complete, add resolver-specific `dig` checks for both zones against every advertised resolver and confirm the application connection itself goes directly to the site Caddy.
DERP or peer relay remains a transport fallback rather than the expected steady-state peer path.

## Primary references

- [Caddy Dynamic DNS module](https://github.com/mholt/caddy-dynamicdns)
- [Caddy reverse proxy directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
- [Caddy proxying to another Caddy](https://caddyserver.com/docs/caddyfile/patterns)
- [Caddy request matchers](https://caddyserver.com/docs/caddyfile/matchers)
- [Technitium DNS Server](https://technitium.com/dns/)
- [Technitium clustering design](https://blog.technitium.com/2025/11/understanding-clustering-and-how-to.html)
- [Tailscale connection types](https://tailscale.com/docs/reference/connection-types)
- [Tailscale DNS](https://tailscale.com/docs/reference/dns-in-tailscale)
- [Tailscale site-to-site networking](https://tailscale.com/docs/features/site-to-site)
