from __future__ import annotations

import json
import os
from pathlib import Path
from collections.abc import Sequence

from .command import run_command
from .models import CommandResult, ContainerState
from .timing import wait_until


def parse_container_state(payload: str, name: str = "") -> ContainerState:
    decoded = json.loads(payload)
    item = decoded[0] if isinstance(decoded, list) else decoded
    state = item.get("State", {})
    health_value = state.get("Health", {}).get("Status")
    return ContainerState(
        name=name or item.get("Name", "").lstrip("/"),
        status=state.get("Status", "unknown"), health=health_value,
        running=bool(state.get("Running", False)),
    )


class DockerClient:
    def __init__(self, compose_file: str | Path | None = None,
                 validation_compose_file: str | Path | None = None,
                 command_timeout: float = 120.0,
                 additional_compose_files: Sequence[str | Path] | None = None):
        self.compose_file = Path(compose_file or os.getenv("VALIDATION_COMPOSE_FILE", "docker-compose.yml"))
        self.validation_compose_file = Path(validation_compose_file or os.getenv("VALIDATION_OVERRIDE_FILE", "docker-compose.validation.yml"))
        self.command_timeout = command_timeout
        self.compose_files = [self.compose_file, self.validation_compose_file]
        self.compose_files.extend(Path(value) for value in (additional_compose_files or []))

    def _compose(self, arguments: Sequence[str], timeout: float | None = None) -> CommandResult:
        return run_command(
            ["docker", "compose",
             *(part for path in self.compose_files for part in ("-f", str(path))),
             *arguments],
            timeout=timeout or self.command_timeout,
        )

    def with_additional_compose_files(
        self, compose_files: Sequence[str | Path]
    ) -> "DockerClient":
        return DockerClient(
            self.compose_file, self.validation_compose_file,
            self.command_timeout, compose_files,
        )

    def compose_exec(self, service: str, command: Sequence[str], timeout: float | None = None) -> CommandResult:
        return self._compose(["exec", "-T", service, *command], timeout)

    def start_service(self, service: str) -> CommandResult:
        return self._compose(["start", service])

    def stop_service(self, service: str) -> CommandResult:
        return self._compose(["stop", service])

    def restart_service(self, service: str) -> CommandResult:
        return self._compose(["restart", service])

    def recreate_services(self, services: Sequence[str]) -> CommandResult:
        if not services:
            raise ValueError("at least one service is required")
        return self._compose(
            ["up", "-d", "--force-recreate", "--no-deps", *services],
            timeout=max(self.command_timeout, 300.0),
        )

    def compose_environment_value(self, service: str, name: str) -> str:
        if not name or not name.replace("_", "").isalnum():
            raise ValueError(f"Invalid environment variable name: {name}")
        return self.compose_exec(service, ["printenv", name]).stdout.strip()

    def inspect_container(self, container_name: str) -> CommandResult:
        return run_command(["docker", "inspect", container_name], timeout=self.command_timeout)

    def get_container_state(self, container_name: str) -> ContainerState:
        return parse_container_state(self.inspect_container(container_name).stdout, container_name)

    def get_container_status(self, container_name: str) -> str:
        return self.get_container_state(container_name).status

    def get_container_health(self, container_name: str) -> str | None:
        return self.get_container_state(container_name).health

    def get_service_container_id(self, service: str) -> str:
        result = self._compose(["ps", "-q", service])
        container_id = result.stdout.strip()
        if not container_id:
            raise LookupError(f"No container found for Compose service {service}")
        return container_id

    def wait_for_container_healthy(self, container_name: str, timeout: float) -> ContainerState:
        return wait_until(
            lambda: (state if (state := self.get_container_state(container_name)).health == "healthy" else None),
            timeout, 2.0, f"container {container_name} to become healthy",
        )

    def wait_for_service_running(self, service: str, timeout: float) -> bool:
        def running() -> bool:
            result = self._compose(["ps", "--status", "running", "--services"])
            return service in {line.strip() for line in result.stdout.splitlines()}
        return wait_until(running, timeout, 2.0, f"service {service} to be running")

    def wait_for_service_healthy(self, service: str, timeout: float) -> ContainerState:
        return self.wait_for_container_healthy(self.get_service_container_id(service), timeout)
