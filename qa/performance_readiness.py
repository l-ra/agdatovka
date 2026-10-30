"""Validate AGDA-13 readiness manifests without executing load or network I/O."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCENARIOS = ROOT / "qa" / "performance-scenarios.json"
FIXTURES = ROOT / "qa" / "fixtures.json"


def validate() -> list[str]:
    errors: list[str] = []
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    if scenarios["status"] != "scenario-ready-not-measured":
        errors.append("manifest must not claim measured performance")
    if scenarios["fixtureProfile"] != fixtures["profile"] or scenarios["seed"] != fixtures["seed"]:
        errors.append("scenario and fixture profiles must match")
    if scenarios["target"]["acceptedMessagesPerMinute"] < 1000:
        errors.append("target must cover 1,000 messages/minute")
    if len(scenarios["scenarios"]) < 10:
        errors.append("all readiness scenario families must be present")
    ids = [item["id"] for item in scenarios["scenarios"]]
    if len(ids) != len(set(ids)):
        errors.append("scenario IDs must be unique")
    required = set(scenarios["requiredEvidence"])
    for item in ("commit", "seed", "counts", "checksums", "cleanup_proof"):
        if item not in required:
            errors.append(f"required evidence missing: {item}")
    if scenarios["endpointPolicy"]["productionDnsAllowed"] or scenarios["endpointPolicy"]["credentialsAllowed"]:
        errors.append("production DNS and credentials must remain disabled")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("AGDA-13 readiness manifest valid; load execution was not run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
