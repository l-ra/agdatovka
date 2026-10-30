"""Metrics collector used by future performance runs; it executes no load."""
from dataclasses import dataclass, field
from time import monotonic

@dataclass
class MetricsCollector:
    started: float = field(default_factory=monotonic)
    counters: dict[str, int] = field(default_factory=dict)
    samples: dict[str, list[float]] = field(default_factory=dict)
    def count(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value
    def observe(self, name: str, value: float) -> None:
        self.samples.setdefault(name, []).append(value)
    def snapshot(self) -> dict[str, object]:
        return {"counters": dict(sorted(self.counters.items())), "samples": {k: list(v) for k, v in sorted(self.samples.items())}, "uptimeSeconds": max(0.0, monotonic() - self.started)}
