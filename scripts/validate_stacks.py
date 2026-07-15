#!/usr/bin/env python3
"""Validate Komodo stack metadata and Docker Compose inputs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAILSCALE_IP = re.compile(r"\b100\.(?:\d{1,3}\.){2}\d{1,3}\b")
ALLOWED_TAILSCALE_CIDR = "100.64.0.0/10"


def resolve_path(path: str, run_directory: Path) -> Path:
    root_path = ROOT / path
    if root_path.exists():
        return root_path
    return run_directory / path


def validate_stack_file(stack_file: Path) -> list[str]:
    errors: list[str] = []
    try:
        document = tomllib.loads(stack_file.read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"{stack_file.relative_to(ROOT)}: {error}"]

    stacks = document.get("stack", [])
    if not stacks:
        return [f"{stack_file.relative_to(ROOT)}: no [[stack]] entry"]

    for stack in stacks:
        config = stack.get("config", {})
        run_directory = ROOT / config.get("run_directory", ".")
        compose_files = [
            resolve_path(path, run_directory)
            for path in config.get("file_paths", [])
        ]

        if not compose_files:
            errors.append(f"{stack_file.relative_to(ROOT)}: no Compose file_paths")
            continue

        missing = [path for path in compose_files if not path.is_file()]
        for path in missing:
            errors.append(
                f"{stack_file.relative_to(ROOT)}: missing {path.relative_to(ROOT)}"
            )

        for config_file in config.get("config_files", []):
            path = resolve_path(config_file["path"], run_directory)
            if not path.is_file():
                errors.append(
                    f"{stack_file.relative_to(ROOT)}: missing {path.relative_to(ROOT)}"
                )

        env_file_path = config.get("env_file_path")
        if env_file_path and any(
            "KOMODO_ENV_FILE" in path.read_text()
            for path in compose_files
            if path.is_file()
        ):
            expected_assignment = f"KOMODO_ENV_FILE={env_file_path}"
            environment = config.get("environment", "").splitlines()
            if expected_assignment not in environment:
                errors.append(
                    f"{stack_file.relative_to(ROOT)}: Compose expects "
                    f"{expected_assignment}"
                )

        if missing or shutil.which("docker") is None:
            continue

        command = ["docker", "compose"]
        for compose_file in compose_files:
            command.extend(["-f", str(compose_file)])
        command.extend(["config", "--no-interpolate", "--format", "json"])
        result = subprocess.run(
            command,
            cwd=run_directory,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            errors.append(
                f"{stack_file.relative_to(ROOT)}: Compose validation failed: {detail}"
            )
            continue

        try:
            rendered = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            errors.append(
                f"{stack_file.relative_to(ROOT)}: invalid Compose JSON: {error}"
            )
            continue

        for service_name, service in rendered.get("services", {}).items():
            if service.get("restart") not in {"always", "unless-stopped"}:
                errors.append(
                    f"{stack_file.relative_to(ROOT)}: {service_name} has no restart policy"
                )

    return errors


def validate_repository_policy() -> list[str]:
    errors: list[str] = []
    env_file_owners: dict[Path, Path] = {}

    for stack_file in sorted((ROOT / "services").rglob("stack.toml")):
        document = tomllib.loads(stack_file.read_text())
        for stack in document.get("stack", []):
            config = stack.get("config", {})
            env_file_path = config.get("env_file_path")
            if not env_file_path:
                errors.append(
                    f"{stack_file.relative_to(ROOT)}: explicit env_file_path required"
                )
                continue

            relative_env_path = Path(env_file_path)
            if relative_env_path.is_absolute() or ".." in relative_env_path.parts:
                errors.append(
                    f"{stack_file.relative_to(ROOT)}: env_file_path must stay "
                    "inside run_directory"
                )
                continue

            run_directory = ROOT / config.get("run_directory", ".")
            rendered_env_path = (run_directory / relative_env_path).resolve()
            if owner := env_file_owners.get(rendered_env_path):
                errors.append(
                    f"{stack_file.relative_to(ROOT)}: env_file_path is shared with "
                    f"{owner.relative_to(ROOT)}"
                )
            else:
                env_file_owners[rendered_env_path] = stack_file

    for path in sorted((ROOT / "services").rglob("*")):
        if not path.is_file() or path.suffix not in {".yaml", ".yml", ".toml"}:
            continue
        text = path.read_text()
        if "SOCKY_PROXY_BIND_IP" in text:
            errors.append(f"{path.relative_to(ROOT)}: obsolete Tailnet bind variable")
        scrubbed = text.replace(ALLOWED_TAILSCALE_CIDR, "")
        if TAILSCALE_IP.search(scrubbed):
            errors.append(f"{path.relative_to(ROOT)}: hard-coded Tailscale host IP")
    return errors


def main() -> int:
    errors: list[str] = []
    stack_files = sorted((ROOT / "services").rglob("stack.toml"))
    for stack_file in stack_files:
        errors.extend(validate_stack_file(stack_file))
    errors.extend(validate_repository_policy())

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    compose_note = "with Compose rendering" if shutil.which("docker") else "without Docker"
    print(f"Validated {len(stack_files)} stack definitions {compose_note}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
