"""Synthetic observability primitives with content-safe defaults.

Telemetry is metadata only: payloads, bearer tokens, credentials, and private
key material are rejected or redacted before a record can be emitted.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Mapping


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_KEY = re.compile(r"(?:authorization|access.?token|refresh.?token|password|secret|private.?key|content|payload|body|raw.?xml|raw.?bytes)", re.I)
_PRIVATE_KEY = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----", re.I)


def _safe_id(value: str | None, prefix: str) -> str:
    if value and _ID.fullmatch(value):
        return value
    return f"{prefix}_{secrets.token_hex(12)}"


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    correlation_id: str
    operation_id: str

    @classmethod
    def create(cls, request_id: str | None = None, correlation_id: str | None = None, operation_id: str | None = None) -> "RequestContext":
        request = _safe_id(request_id, "req")
        return cls(request, _safe_id(correlation_id or request, "corr"), _safe_id(operation_id, "op"))

    def as_dict(self) -> dict[str, str]:
        return {"requestId": self.request_id, "correlationId": self.correlation_id, "operationId": self.operation_id}


def redact(value: Any, *, key: str = "") -> Any:
    """Return JSON-compatible metadata with sensitive fields removed."""
    if _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item, key=key) for item in value]
    if isinstance(value, str):
        if _PRIVATE_KEY.search(value) or value.lower().startswith(("bearer ", "token ")):
            return "[REDACTED]"
        return value[:256]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return "[REDACTED]"


@dataclass
class TraceSampler:
    rate: float = 0.05

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate <= 1.0:
            raise ValueError("sampling rate must be between 0 and 1")

    def include(self, trace_id: str, *, outcome: str = "success", force: bool = False) -> bool:
        if force or outcome in {"error", "denied", "dead_letter"}:
            return True
        bucket = int(hashlib.sha256(trace_id.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
        return bucket < self.rate


@dataclass
class Telemetry:
    sampler: TraceSampler = field(default_factory=TraceSampler)
    counters: dict[str, int] = field(default_factory=dict)
    latency_ms: dict[str, list[float]] = field(default_factory=dict)
    records: list[dict[str, Any]] = field(default_factory=list)

    def count(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def observe(self, name: str, milliseconds: float) -> None:
        if milliseconds < 0:
            raise ValueError("latency cannot be negative")
        self.latency_ms.setdefault(name, []).append(round(milliseconds, 3))

    def emit(self, event: str, context: RequestContext, *, outcome: str = "success", trace_id: str | None = None, **fields: Any) -> dict[str, Any] | None:
        trace = trace_id or context.operation_id
        if not self.sampler.include(trace, outcome=outcome):
            return None
        record = {"event": event, "outcome": outcome, **context.as_dict(), "traceId": trace, **redact(fields)}
        self.records.append(record)
        return record

    def worker_result(self, *, status: str, attempts: int, latency_ms: float) -> None:
        self.count(f"worker_{status}")
        self.count("worker_attempts", attempts)
        self.observe("worker_latency_ms", latency_ms)

    def snapshot(self) -> dict[str, Any]:
        return {"counters": dict(sorted(self.counters.items())), "latencyMs": {k: list(v) for k, v in sorted(self.latency_ms.items())}, "recordCount": len(self.records)}


def alert_conditions(snapshot: Mapping[str, Any], *, dead_letter_threshold: int = 1, backpressure_threshold: int = 1) -> list[str]:
    counters = snapshot.get("counters", {})
    alerts = []
    if counters.get("queue_dead_lettered", 0) >= dead_letter_threshold:
        alerts.append("dead_letter_rate")
    if counters.get("backpressure_rejected", 0) + counters.get("tenant_backpressure_rejected", 0) >= backpressure_threshold:
        alerts.append("backpressure")
    return alerts


@dataclass
class AuditLedger:
    """Small offline hash-chain used to test tamper detection and rebuild."""
    events: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event: Mapping[str, Any]) -> dict[str, Any]:
        item = {k: redact(v, key=str(k)) for k, v in event.items() if k not in {"eventDigest", "previousDigest"}}
        item["previousDigest"] = self.events[-1]["eventDigest"] if self.events else None
        item["eventDigest"] = "sha256:" + hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.events.append(item)
        return dict(item)

    def verify(self) -> bool:
        previous = None
        for item in self.events:
            if item.get("previousDigest") != previous:
                return False
            digest = item.get("eventDigest")
            body = {k: v for k, v in item.items() if k != "eventDigest"}
            expected = "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if digest != expected:
                return False
            previous = digest
        return True

    def rebuild(self) -> "AuditLedger":
        rebuilt = AuditLedger()
        for item in self.events:
            rebuilt.append(item)
        return rebuilt
