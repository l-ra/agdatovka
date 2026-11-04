"""Deterministic runtime configuration for the deployable service boundary.

The management API remains dependency-free for fixtures.  This module defines
the production wiring contract so a deployment cannot accidentally start with
the SQLite fixture, an ephemeral object store, or an in-process queue.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Raised when a runtime configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    host: str
    port: int
    database_url: str
    object_store_url: str
    queue_url: str
    auth_profile: str
    max_upload_bytes: int = 16 * 1024 * 1024

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "RuntimeConfig":
        values = dict(os.environ if environ is None else environ)
        environment = values.get("AG_ENV", "development").strip().lower()
        if environment not in {"development", "test", "deploy", "production"}:
            raise ConfigurationError("AG_ENV must be development, test, deploy, or production")
        try:
            port = int(values.get("AG_PORT", "8080"))
            max_upload = int(values.get("AG_MAX_UPLOAD_BYTES", str(16 * 1024 * 1024)))
        except ValueError as exc:
            raise ConfigurationError("AG_PORT and AG_MAX_UPLOAD_BYTES must be integers") from exc
        if not 1 <= port <= 65535 or max_upload <= 0:
            raise ConfigurationError("AG_PORT or AG_MAX_UPLOAD_BYTES is outside its allowed range")
        config = cls(
            environment=environment,
            host=values.get("AG_HOST", "0.0.0.0"),
            port=port,
            database_url=values.get("DATABASE_URL", "sqlite:///data/ag-datovka.sqlite3"),
            object_store_url=values.get("OBJECT_STORE_URL", "file:///data/objects"),
            queue_url=values.get("QUEUE_URL", "memory://synthetic"),
            auth_profile=values.get("AG_AUTH_PROFILE", "test"),
            max_upload_bytes=max_upload,
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.environment in {"deploy", "production"}:
            if urlsplit(self.database_url).scheme not in {"postgres", "postgresql"}:
                raise ConfigurationError("deploy and production require DATABASE_URL=postgresql://...")
            if urlsplit(self.object_store_url).scheme not in {"http", "https", "s3"}:
                raise ConfigurationError("deploy and production require persistent OBJECT_STORE_URL")
            if urlsplit(self.queue_url).scheme not in {"redis", "rediss", "amqp", "amqps"}:
                raise ConfigurationError("deploy and production require a durable QUEUE_URL")
            if self.auth_profile not in {"deploy", "production"}:
                raise ConfigurationError("deploy and production require a non-fixture AG_AUTH_PROFILE")

