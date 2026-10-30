"""Deterministic, unmistakably synthetic fixtures."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

SEED = 20261030
PROFILE = "synthetic-ag-v1-2026-10-30"

def message_fixtures() -> list[dict[str, Any]]:
    return [
        {"id": "msg-empty", "size": 0, "expected": "accepted"},
        {"id": "msg-minimal", "size": 16, "expected": "accepted"},
        {"id": "msg-boundary", "size": 16 * 1024 * 1024, "expected": "accepted"},
        {"id": "msg-over-limit", "size": 16 * 1024 * 1024 + 1, "expected": "rejected:content_too_large"},
        {"id": "att-corrupt-checksum", "size": 32, "expected": "rejected:checksum_mismatch"},
        {"id": "att-unsupported-type", "size": 12, "expected": "rejected:unsupported_type"},
    ]

def lifecycle_fixtures() -> list[dict[str, Any]]:
    return [
        {"id": "life-submit-deliver-login", "events": ["EV0", "EV2", "EV3"], "expected": "read"},
        {"id": "life-submit-fikce", "events": ["EV0", "EV2", "EV5"], "expected": "fiction"},
        {"id": "life-undeliverable", "events": ["EV0", "EV6"], "expected": "undeliverable"},
        {"id": "life-failed", "events": ["EV0", "EV8"], "expected": "failed"},
        {"id": "life-weekend-holiday", "events": ["EV0", "EV11"], "expected": "holiday-clock"},
    ]

def fault_fixtures() -> list[dict[str, Any]]:
    return [{"id": f"fault-{name}", "fault": name, "retryable": name in {"timeout", "upstream_429", "upstream_5xx", "worker_crash_after_side_effect", "object_store_delay"}} for name in ("timeout", "upstream_429", "upstream_5xx", "malformed_response", "duplicate_response", "worker_crash_after_side_effect", "object_store_delay", "queue_poison")]

def load_manifest(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or Path(__file__).with_name("fixtures.json")).read_text(encoding="utf-8"))
