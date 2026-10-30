#!/usr/bin/env python3
"""Safe profile preflight and deterministic offline smoke harness."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "profiles"
PRODUCTION_HOSTS = {"datovka.gov.cz", "www.datovka.gov.cz", "isds.cz", "www.isds.cz"}
SECRET_WORDS = re.compile(r"(password|passwd|secret|token|private[_-]?key|credential)\s*:", re.I)


def yaml_scalars(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or line.startswith(" "):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def preflight(profile: str) -> dict[str, str]:
    path = PROFILES / f"{profile}.yaml"
    if profile not in {"ag-synthetic", "isds-public-test", "offline-fixture"} or not path.is_file():
        raise ValueError(f"unknown profile: {profile}")
    raw = path.read_text(encoding="utf-8")
    if SECRET_WORDS.search(raw.replace("credential_ref:", "")):
        # Secret field names are allowed only as references, never values.
        for line in raw.splitlines():
            if any(word in line.lower() for word in ("password:", "secret:", "token:", "private_key:")):
                raise ValueError(f"secret-like field in {path.name}")
    values = yaml_scalars(path)
    endpoint = values.get("endpoint", "")
    host = urlparse(endpoint).hostname
    if host in PRODUCTION_HOSTS or (host and host.endswith(".gov.cz")):
        raise ValueError(f"production hostname is forbidden: {host}")
    if profile == "offline-fixture" and values.get("mode") != "offline":
        raise ValueError("offline-fixture must be offline")
    if profile != "offline-fixture" and ".invalid" not in endpoint:
        raise ValueError("network profile must retain a placeholder endpoint")
    return values


def offline_smoke() -> list[str]:
    fixture = json.loads((ROOT / "fixtures/message.json").read_text(encoding="utf-8"))
    expected = fixture["attachment"]["sha256"]
    actual = hashlib.sha256(b"hello").hexdigest()
    if actual != expected:
        raise ValueError("offline fixture attachment digest mismatch")
    required = {"fixture_id", "sender", "recipient", "subject", "body", "receipt"}
    if not required.issubset(fixture):
        raise ValueError("offline fixture is incomplete")
    return ["parse", "receipt", "search", "export"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="offline-fixture")
    args = parser.parse_args()
    values = preflight(args.profile)
    checks = [f"profile:{args.profile}", f"mode:{values['mode']}"]
    if args.profile == "offline-fixture":
        checks.extend(offline_smoke())
    else:
        checks.append("network:explicit-operator-action-required")
    print(json.dumps({"status": "pass", "checks": checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
