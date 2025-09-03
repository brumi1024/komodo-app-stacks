# Homelab Komodo Stacks

This repository contains application stacks deployed via Komodo using GitOps. All stacks depend on secrets being synchronized from 1Password by the `komodo-op` service.

## Architecture

```
1Password Vault → komodo-op → Komodo Global Variables → Application Stacks
```

## Stack Overview

| Stack | Description | Services | Server |
|-------|-------------|----------|--------|
| `servarr` | Media automation | Radarr, Sonarr, Jackett, Bazarr | home-server |
| `monitoring` | System monitoring | Prometheus, Grafana, Node Exporter | home-server |
| `homepage` | Dashboard | Homepage | home-server |

## Prerequisites

1. **komodo-op deployed**: Must be running and syncing secrets from 1Password
2. **Komodo resource sync**: Must be configured to monitor this repository
3. **Required secrets**: All referenced secrets must exist in 1Password

## Directory Structure

```
homelab-komodo-stacks/
├── servarr/
│   ├── docker-compose.yaml
│   └── stack.toml
├── monitoring/
│   ├── docker-compose.yaml
│   └── stack.toml
├── homepage/
│   ├── docker-compose.yaml
│   └── stack.toml
├── renovate.json
└── README.md
```

## Deployment Flow

1. **Push changes** to this repository
2. **GitHub webhook** triggers Komodo resource sync
3. **Komodo syncs** new configurations
4. **Auto-deploy** occurs if enabled in stack.toml
5. **Services start** with secrets from Komodo global variables

## Required 1Password Secrets

These secrets must be synced by komodo-op before deploying stacks:

### Media Stack (servarr)
- `MEDIA_CONFIG_DIR`: Configuration directory path
- `MEDIA_DOWNLOADS_DIR`: Downloads directory path  
- `MEDIA_MOVIES_DIR`: Movies directory path
- `MEDIA_TV_DIR`: TV shows directory path
- `RADARR_API_KEY`: Radarr API key
- `SONARR_API_KEY`: Sonarr API key
- `JACKETT_API_KEY`: Jackett API key

### Monitoring Stack
- `MONITORING_CONFIG_DIR`: Monitoring config directory
- `MONITORING_DATA_DIR`: Monitoring data directory
- `GRAFANA_ADMIN_PASSWORD`: Grafana admin password

### Homepage Stack
- `HOMEPAGE_CONFIG_DIR`: Homepage config directory

## Adding New Stacks

1. **Create directory** for your stack
2. **Add docker-compose.yaml** with your services
3. **Create stack.toml** with deployment configuration
4. **Reference secrets** using `[[SECRET_NAME]]` syntax
5. **Commit and push** - auto-deployment will occur

### Example stack.toml
```toml
[[stack]]
name = "my-stack"
tags = ["category", "service-type"]

[stack.config]
server = "home-server"
auto_update = true
git_account = "benjaminteke"
repo = "benjaminteke/homelab-komodo-stacks"
branch = "main"
file_paths = ["my-stack/docker-compose.yaml"]

environment = """
SECRET_VALUE=[[MY_SECRET_FROM_1PASSWORD]]
CONFIG_DIR=[[MY_CONFIG_DIR]]
"""
```

## Security

- **No secrets in repository**: All secrets come from 1Password via komodo-op
- **Environment variables**: Use Komodo global variables for all sensitive data
- **Access control**: Repository access controls who can deploy what

## Monitoring Deployments

- **Komodo UI**: View deployment status and logs
- **GitHub Actions**: See webhook delivery status
- **Container logs**: Check individual service logs in Komodo

## Troubleshooting

### Stack won't deploy
1. Check if komodo-op is running and syncing secrets
2. Verify all referenced secrets exist in Komodo global variables
3. Check Komodo resource sync status

### Missing secrets
1. Ensure secret exists in 1Password "Homelab" vault
2. Verify komodo-op has synced recently (check logs)
3. Check secret name matches exactly in stack.toml

### Docker compose errors
1. Check image availability and tags
2. Verify volume paths exist on target server
3. Review port conflicts with other services