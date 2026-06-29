from __future__ import annotations

from dataclasses import dataclass
import os


MNEMOSYNE_SERVICE_HOST_ENV = "MNEMOSYNE_SERVICE_HOST"
MNEMOSYNE_SERVICE_PORT_ENV = "MNEMOSYNE_SERVICE_PORT"
MNEMOSYNE_SERVICE_MODE_ENV = "MNEMOSYNE_SERVICE_MODE"


@dataclass(frozen=True)
class ServiceConfig:
    host: str = "127.0.0.1"
    port: int = 8088
    mode: str = "local"

    @property
    def bind(self) -> tuple[str, int]:
        return (self.host, self.port)


def service_config_from_env() -> ServiceConfig:
    raw_port = os.environ.get(MNEMOSYNE_SERVICE_PORT_ENV, "8088")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(
            f"{MNEMOSYNE_SERVICE_PORT_ENV} must be an integer, got {raw_port!r}"
        ) from exc

    return ServiceConfig(
        host=os.environ.get(MNEMOSYNE_SERVICE_HOST_ENV, "127.0.0.1"),
        port=port,
        mode=os.environ.get(MNEMOSYNE_SERVICE_MODE_ENV, "local"),
    )
