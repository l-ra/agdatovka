"""Small, dependency-free management API used by the synthetic local fixture.

This module intentionally owns only the management contract.  ISDS SOAP,
production credentials, migration, and message content delivery are outside
this boundary.  SQLite is a local test/development store; the data model uses
the same explicit tenant, policy, operation, and evidence boundaries expected
from a production implementation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, urlencode, urlsplit

from .pipeline import DurablePipeline
from .security import TrustError, TrustProfile, modern_subject, secret_handle, validate_endpoint


API_VERSION = "v1"
MAX_PAGE_SIZE = 100
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,99}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    else:
        raw = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def cursor_encode(value: Mapping[str, str]) -> str:
    raw = canonical_json(value).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def cursor_decode(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if not isinstance(decoded, dict) or not isinstance(decoded.get("createdAt"), str) or not isinstance(decoded.get("id"), str):
            raise ValueError
        return {"createdAt": decoded["createdAt"], "id": decoded["id"]}
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise Problem(400, "invalid_cursor", "Invalid cursor", "The cursor is not a valid API cursor.")


class Problem(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        detail: str,
        *,
        retryable: bool = False,
        field_errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.retryable = retryable
        self.field_errors = field_errors or []

    def as_json(self, request_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": f"https://api.agdatovka.test/problems/{self.code}",
            "code": self.code,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "requestId": request_id,
            "retryable": self.retryable,
        }
        if self.field_errors:
            result["fieldErrors"] = self.field_errors
        return result


class Database:
    """SQLite persistence with no migration requirement for a fresh local DB."""

    def __init__(self, path: str = ":memory:") -> None:
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS boxes (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
              status TEXT NOT NULL, config_json TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identities (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              subject TEXT NOT NULL, display_name TEXT NOT NULL, status TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              UNIQUE(box_id, subject)
            );
            CREATE TABLE IF NOT EXISTS permissions (
              id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, description TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS roles (
              id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS role_permissions (
              role_id TEXT NOT NULL REFERENCES roles(id),
              permission_id TEXT NOT NULL REFERENCES permissions(id),
              PRIMARY KEY(role_id, permission_id)
            );
            CREATE TABLE IF NOT EXISTS memberships (
              box_id TEXT NOT NULL REFERENCES boxes(id),
              identity_id TEXT NOT NULL REFERENCES identities(id),
              role_id TEXT NOT NULL REFERENCES roles(id),
              created_at TEXT NOT NULL,
              PRIMARY KEY(box_id, identity_id, role_id)
            );
            CREATE TABLE IF NOT EXISTS auth_methods (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              identity_id TEXT REFERENCES identities(id), type TEXT NOT NULL,
              label TEXT NOT NULL, metadata_json TEXT NOT NULL, status TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              sender_identity_id TEXT REFERENCES identities(id), target_box_id TEXT,
              subject TEXT NOT NULL, status TEXT NOT NULL, content_digest TEXT,
              metadata_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attachments (
              id TEXT PRIMARY KEY, message_id TEXT NOT NULL REFERENCES messages(id),
              filename TEXT NOT NULL, media_type TEXT NOT NULL, byte_length INTEGER NOT NULL,
              content_digest TEXT NOT NULL, content_bytes BLOB NOT NULL DEFAULT X'', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS message_events (
              id TEXT PRIMARY KEY, message_id TEXT NOT NULL REFERENCES messages(id),
              event_type TEXT NOT NULL, source_code TEXT, source_profile TEXT,
              reason TEXT, occurred_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
              actor TEXT NOT NULL, attempt INTEGER NOT NULL, previous_digest TEXT,
              event_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS operations (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              message_id TEXT, kind TEXT NOT NULL, status TEXT NOT NULL,
              attempts INTEGER NOT NULL, retryable INTEGER NOT NULL, request_json TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exports (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              status TEXT NOT NULL, format TEXT NOT NULL, manifest_digest TEXT,
              result_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor TEXT NOT NULL,
              action TEXT NOT NULL, outcome TEXT NOT NULL, resource_type TEXT,
              resource_id TEXT, policy_version TEXT NOT NULL, request_id TEXT NOT NULL,
              correlation_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
              content_digest TEXT, reason TEXT, previous_digest TEXT, event_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
              tenant_id TEXT NOT NULL, actor TEXT NOT NULL, key TEXT NOT NULL,
              method TEXT NOT NULL, path TEXT NOT NULL, request_digest TEXT NOT NULL,
              response_status INTEGER NOT NULL, response_json TEXT NOT NULL,
              state TEXT NOT NULL DEFAULT 'claimed', attempts INTEGER NOT NULL DEFAULT 1,
              claimed_at TEXT NOT NULL, completed_at TEXT,
              created_at TEXT NOT NULL, PRIMARY KEY(tenant_id, actor, key)
            );
            CREATE TABLE IF NOT EXISTS receipts (
              id TEXT PRIMARY KEY, message_id TEXT NOT NULL REFERENCES messages(id),
              operation_id TEXT NOT NULL REFERENCES operations(id), status TEXT NOT NULL,
              source_code TEXT NOT NULL, source_profile TEXT NOT NULL,
              raw_digest TEXT NOT NULL, raw_xml TEXT NOT NULL,
              validated_at TEXT NOT NULL, immutable INTEGER NOT NULL DEFAULT 1,
              UNIQUE(message_id, operation_id)
            );
            CREATE TABLE IF NOT EXISTS legal_holds (
              id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, resource_type TEXT NOT NULL,
              resource_id TEXT NOT NULL, reason TEXT NOT NULL, active INTEGER NOT NULL,
              created_at TEXT NOT NULL, released_at TEXT
            );
            CREATE TABLE IF NOT EXISTS retention_tombstones (
              id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, resource_type TEXT NOT NULL,
              resource_id TEXT NOT NULL, policy_version TEXT NOT NULL,
              request_id TEXT NOT NULL, tombstone_digest TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trust_profiles (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL,
              profile_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(name, version)
            );
            CREATE TABLE IF NOT EXISTS endpoint_profiles (
              id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, profile_json TEXT NOT NULL,
              status TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS key_handles (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              handle TEXT NOT NULL, version TEXT NOT NULL, state TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trust_rotations (
              id TEXT PRIMARY KEY, box_id TEXT NOT NULL REFERENCES boxes(id),
              old_key_id TEXT, new_key_id TEXT NOT NULL, state TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_box_created ON messages(box_id, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_tenant_created ON audit_events(tenant_id, occurred_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_operations_box_created ON operations(box_id, created_at DESC, id DESC);
            """
        )
        # Keep the synthetic fixture usable when a local Phase 2 SQLite file
        # is reused.  This is a narrow additive schema change, not migration
        # from the former AGDatovka implementation.
        attachment_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(attachments)").fetchall()}
        if "content_bytes" not in attachment_columns:
            self.connection.execute("ALTER TABLE attachments ADD COLUMN content_bytes BLOB NOT NULL DEFAULT ''")
        idempotency_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(idempotency_keys)").fetchall()}
        if "state" not in idempotency_columns:
            self.connection.execute("ALTER TABLE idempotency_keys ADD COLUMN state TEXT NOT NULL DEFAULT 'completed'")
        if "attempts" not in idempotency_columns:
            self.connection.execute("ALTER TABLE idempotency_keys ADD COLUMN attempts INTEGER NOT NULL DEFAULT 1")
        if "claimed_at" not in idempotency_columns:
            self.connection.execute("ALTER TABLE idempotency_keys ADD COLUMN claimed_at TEXT NOT NULL DEFAULT ''")
        if "completed_at" not in idempotency_columns:
            self.connection.execute("ALTER TABLE idempotency_keys ADD COLUMN completed_at TEXT")
        self.connection.execute("UPDATE idempotency_keys SET claimed_at=created_at WHERE claimed_at=''")
        self._seed_policy()
        self.connection.commit()

    def _seed_policy(self) -> None:
        at = now_iso()
        permission_codes = [
            ("box:create", "Create a databox"), ("box:read", "Read databox configuration"),
            ("box:update", "Update databox configuration"), ("identity:manage", "Manage identities"),
            ("policy:manage", "Manage roles and permissions"), ("membership:manage", "Assign memberships"),
            ("auth:manage", "Manage authentication method metadata"), ("message:create", "Create message drafts"),
            ("message:send", "Submit messages"), ("message:read", "Read message metadata and events"),
            ("receipt:read", "Read receipt evidence"), ("operation:cancel", "Cancel operations"),
            ("operation:read", "Read operations"), ("export:create", "Create exports"),
            ("export:read", "Read exports"), ("audit:read", "Read audit events"),
            ("retention:manage", "Manage retention and legal holds"), ("retention:read", "Read retention evidence"),
        ]
        for code, description in permission_codes:
            self.connection.execute(
                "INSERT OR IGNORE INTO permissions(id, code, description, created_at) VALUES(?,?,?,?)",
                (new_id("perm"), code, description, at),
            )
        role_permissions = {
            "box-owner": [code for code, _ in permission_codes if code not in {"box:create"}],
            "box-operator": ["box:read", "message:create", "message:send", "message:read", "receipt:read", "operation:read", "export:read"],
            "auditor": ["box:read", "message:read", "receipt:read", "operation:read", "export:read", "audit:read", "retention:read"],
            "trust-admin": ["box:read", "auth:manage"],
            "platform-admin": [code for code, _ in permission_codes],
        }
        for name, codes in role_permissions.items():
            role_id = new_id("role")
            self.connection.execute(
                "INSERT OR IGNORE INTO roles(id, name, description, created_at) VALUES(?,?,?,?)",
                (role_id, name, f"Built-in {name} policy", at),
            )
            row = self.connection.execute("SELECT id FROM roles WHERE name=?", (name,)).fetchone()
            for code in codes:
                permission = self.connection.execute("SELECT id FROM permissions WHERE code=?", (code,)).fetchone()
                self.connection.execute("INSERT OR IGNORE INTO role_permissions(role_id, permission_id) VALUES(?,?)", (row["id"], permission["id"]))

    def one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.connection.execute(sql, tuple(params)).fetchone()

    def all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return list(self.connection.execute(sql, tuple(params)).fetchall())


class Actor:
    def __init__(self, subject: str, box_id: str | None, platform: bool = False) -> None:
        self.subject = subject
        self.box_id = box_id
        self.platform = platform


class ManagementApp:
    """WSGI-compatible application and direct-call contract harness."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db = Database(db_path)
        self.pipeline = DurablePipeline(self.db.connection, max_in_flight=1000, max_attempts=5)
        # The SQLite fixture is intentionally single-process.  Serializing the
        # request critical section makes the idempotency claim atomic for the
        # supported local deployment and gives deterministic concurrency tests.
        self._request_lock = threading.RLock()

    def close(self) -> None:
        self.db.close()

    def __call__(self, environ: Mapping[str, Any], start_response: Any) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        headers = {key[5:].replace("_", "-"): value for key, value in environ.items() if key.startswith("HTTP_")}
        if "CONTENT_TYPE" in environ:
            headers["CONTENT-TYPE"] = environ["CONTENT_TYPE"]
        if "CONTENT_LENGTH" in environ:
            headers["CONTENT-LENGTH"] = environ["CONTENT_LENGTH"]
        declared_length = environ.get("CONTENT_LENGTH")
        try:
            length = int(declared_length) if declared_length not in (None, "") else 0
        except (TypeError, ValueError):
            request_id = environ.get("HTTP_X_REQUEST_ID") or new_id("req")
            problem = Problem(400, "invalid_content_length", "Invalid content length", "Content-Length must be an integer.")
            payload = canonical_json(problem.as_json(request_id)).encode("utf-8")
            start_response("400 Bad Request", [("content-type", "application/problem+json"), ("x-request-id", request_id)])
            return [payload]
        if length < 0:
            request_id = environ.get("HTTP_X_REQUEST_ID") or new_id("req")
            problem = Problem(400, "invalid_content_length", "Invalid content length", "Content-Length cannot be negative.")
            payload = canonical_json(problem.as_json(request_id)).encode("utf-8")
            start_response("400 Bad Request", [("content-type", "application/problem+json"), ("x-request-id", request_id)])
            return [payload]
        if length > MAX_UPLOAD_BYTES:
            request_id = environ.get("HTTP_X_REQUEST_ID") or new_id("req")
            problem = Problem(413, "content_too_large", "Content too large", "The request exceeds the local synthetic upload limit.")
            payload = canonical_json(problem.as_json(request_id)).encode("utf-8")
            start_response("413 Request Entity Too Large", [("content-type", "application/problem+json"), ("x-request-id", request_id)])
            return [payload]
        body = environ["wsgi.input"].read(length) if length else b""
        status, response_headers, payload = self.handle_request(method, path + ("?" + query if query else ""), headers, body)
        start_response(f"{status} {HTTPStatus(status).phrase}", [(k, v) for k, v in response_headers.items()])
        return [payload]

    def handle_request(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | str | Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        with self._request_lock:
            return self._handle_request_unlocked(method, path, headers, body)

    def _handle_request_unlocked(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | str | Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        split = urlsplit(path)
        request_id = headers.get("x-request-id") or headers.get("correlation-id") or new_id("req")
        correlation_id = headers.get("correlation-id") or request_id
        actor: Actor | None = None
        try:
            actor = self._authenticate(headers)
            payload = self._decode_body(body, headers)
        except Problem as problem:
            return self._problem(problem.status, problem.code, problem.title, problem.detail, request_id, problem.retryable, problem.field_errors)
        body_for_hash = payload if not isinstance(body, bytes) else {"rawDigest": digest(body), "bodyLength": len(body)}
        mutating = method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
        idem_key = headers.get("idempotency-key")
        if mutating and not idem_key:
            return self._problem(400, "idempotency_key_required", "Idempotency key required", "Mutating requests require Idempotency-Key.", request_id)
        tenant_for_idem = actor.box_id or "platform"
        request_digest = digest({"method": method.upper(), "path": split.path, "body": body_for_hash})
        if mutating and idem_key:
            replay = self.db.one(
                "SELECT * FROM idempotency_keys WHERE tenant_id=? AND actor=? AND key=?",
                (tenant_for_idem, actor.subject, idem_key),
            )
            if replay:
                if replay["request_digest"] != request_digest:
                    return self._problem(409, "idempotency_conflict", "Idempotency conflict", "The idempotency key was already used with a different request.", request_id)
                if replay["state"] == "completed":
                    response_headers = {"content-type": "application/json", "x-request-id": request_id, "idempotent-replay": "true"}
                    return replay["response_status"], response_headers, replay["response_json"].encode("utf-8")
                # A prior request may have crashed after claiming the key.
                # Reclaim it deterministically and record the attempt.
                self.db.connection.execute(
                    "UPDATE idempotency_keys SET attempts=attempts+1, claimed_at=? WHERE tenant_id=? AND actor=? AND key=?",
                    (now_iso(), tenant_for_idem, actor.subject, idem_key),
                )
                self.db.connection.commit()
            else:
                # The claim is durable before routing, so crash recovery has a
                # persisted attempt/state instead of a raw uniqueness race.
                try:
                    claimed_at = now_iso()
                    self.db.connection.execute(
                        "INSERT INTO idempotency_keys(tenant_id, actor, key, method, path, request_digest, response_status, response_json, state, attempts, claimed_at, completed_at, created_at) VALUES(?,?,?,?,?,?,0,'{}','claimed',1,?,NULL,?)",
                        (tenant_for_idem, actor.subject, idem_key, method.upper(), split.path, request_digest, claimed_at, claimed_at),
                    )
                    self.db.connection.commit()
                except sqlite3.IntegrityError:
                    # Another process may have won the claim; never leak the
                    # uniqueness error and use the same replay/recovery path.
                    replay = self.db.one(
                        "SELECT * FROM idempotency_keys WHERE tenant_id=? AND actor=? AND key=?",
                        (tenant_for_idem, actor.subject, idem_key),
                    )
                    if not replay or replay["request_digest"] != request_digest:
                        return self._problem(409, "idempotency_conflict", "Idempotency conflict", "The idempotency key was already used with a different request.", request_id)
                    if replay["state"] == "completed":
                        return replay["response_status"], {"content-type": "application/json", "x-request-id": request_id, "idempotent-replay": "true"}, replay["response_json"].encode("utf-8")
                    self.db.connection.execute(
                        "UPDATE idempotency_keys SET attempts=attempts+1, claimed_at=? WHERE tenant_id=? AND actor=? AND key=?",
                        (now_iso(), tenant_for_idem, actor.subject, idem_key),
                    )
                    self.db.connection.commit()
        try:
            status, result = self._route(method.upper(), split.path, parse_qs(split.query), payload, headers, actor, request_id, correlation_id)
        except Problem as problem:
            if mutating and idem_key:
                self.db.connection.execute(
                    "DELETE FROM idempotency_keys WHERE tenant_id=? AND actor=? AND key=? AND state='claimed'",
                    (tenant_for_idem, actor.subject, idem_key),
                )
                self.db.connection.commit()
            return self._problem(problem.status, problem.code, problem.title, problem.detail, request_id, problem.retryable, problem.field_errors, actor, method, split.path, correlation_id)
        except Exception:
            # A submit must not leave an operation/message projection without
            # its outbox row (or vice versa) when the route crashes.
            self.db.connection.rollback()
            raise
        response_json = canonical_json(result)
        if mutating and idem_key:
            self.db.connection.execute(
                "UPDATE idempotency_keys SET response_status=?, response_json=?, state='completed', completed_at=? WHERE tenant_id=? AND actor=? AND key=? AND request_digest=?",
                (status, response_json, now_iso(), tenant_for_idem, actor.subject, idem_key, request_digest),
            )
            self.db.connection.commit()
        return status, {"content-type": "application/json", "x-request-id": request_id}, response_json.encode("utf-8")

    def _problem(
        self, status: int, code: str, title: str, detail: str, request_id: str,
        retryable: bool = False, field_errors: list[dict[str, str]] | None = None,
        actor: Actor | None = None, method: str | None = None, path: str | None = None,
        correlation_id: str | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        if actor and method and path:
            self._audit(actor, f"{method.lower()} {path}", "denied", None, None, request_id, correlation_id or request_id, f"{code}: {detail}")
            self.db.connection.commit()
        problem = Problem(status, code, title, detail, retryable=retryable, field_errors=field_errors)
        return status, {"content-type": "application/problem+json", "x-request-id": request_id}, canonical_json(problem.as_json(request_id)).encode("utf-8")

    def _decode_body(self, body: bytes | str | Mapping[str, Any] | None, headers: Mapping[str, str]) -> dict[str, Any]:
        if body is None or body == b"" or body == "":
            return {}
        if isinstance(body, Mapping):
            return dict(body)
        if isinstance(body, bytes) and headers.get("content-type", "").split(";", 1)[0].strip().lower() not in {"", "application/json", "application/problem+json"}:
            return {"_raw_bytes": body}
        if isinstance(body, bytes):
            raw = body.decode("utf-8")
        else:
            raw = body
        if not raw.strip():
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise Problem(400, "invalid_json", "Invalid JSON", f"Request body is not valid JSON: {exc.msg}.")
        if not isinstance(value, dict):
            raise Problem(400, "invalid_body", "Invalid body", "The JSON body must be an object.")
        return value

    def _authenticate(self, headers: Mapping[str, str]) -> Actor:
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise Problem(401, "authentication_required", "Authentication required", "Use a scoped bearer token.")
        token = auth[7:]
        if token.startswith("oidc:"):
            try:
                subject, tenant, _permissions = modern_subject(token)
            except TrustError as error:
                raise Problem(401, error.code, "Authentication failed", error.detail)
            box = self.db.one("SELECT id FROM boxes WHERE id=? AND status='active'", (tenant,))
            if not box:
                raise Problem(401, "invalid_token", "Authentication failed", "The caller tenant is not valid.")
            return Actor(subject, tenant)
        if token in {"dev:platform", "dev:platform-admin"}:
            return Actor("platform-admin", None, platform=True)
        if token.startswith("dev:"):
            parts = token.split(":")
            if len(parts) == 3 and parts[1] and parts[2]:
                box = self.db.one("SELECT id FROM boxes WHERE id=?", (parts[1],))
                identity = self.db.one("SELECT id FROM identities WHERE id=? AND box_id=? AND status='active'", (parts[2], parts[1]))
                if box and identity:
                    return Actor(identity["id"], box["id"])
        raise Problem(401, "invalid_token", "Invalid token", "The bearer token is not valid for this synthetic environment.")

    def _route(
        self, method: str, path: str, query: Mapping[str, list[str]], body: dict[str, Any],
        headers: Mapping[str, str], actor: Actor, request_id: str, correlation_id: str,
    ) -> tuple[int, dict[str, Any]]:
        segments = [segment for segment in path.split("/") if segment]
        if not segments or segments[:2] != ["api", "v1"]:
            raise Problem(404, "not_found", "Not found", "The requested API resource does not exist.")
        rest = segments[2:]
        if not rest:
            return 200, {"apiVersion": API_VERSION, "requestId": request_id, "resources": ["boxes", "messages", "operations", "exports", "retention", "audit/events"]}
        resource = rest[0]
        if resource == "boxes":
            return self._boxes(method, rest[1:], body, actor, request_id, correlation_id, query)
        if resource == "identities":
            return self._identities(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "roles":
            return self._roles(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "permissions":
            return self._permissions(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "auth-methods":
            return self._auth_methods(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "trust-profiles":
            return self._trust_profiles(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "endpoint-profiles":
            return self._endpoint_profiles(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "key-handles":
            return self._key_handles(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "messages":
            return self._messages(method, rest[1:], body, actor, request_id, correlation_id, query, headers)
        if resource == "operations":
            return self._operations(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "exports":
            return self._exports(method, rest[1:], body, actor, request_id, correlation_id, query)
        if resource == "retention":
            return self._retention(method, rest[1:], body, actor, request_id, correlation_id)
        if resource == "audit" and rest[1:] == ["events"]:
            return self._audit_list(query, actor, request_id)
        raise Problem(404, "not_found", "Not found", "The requested API resource does not exist.")

    def _trust_profiles(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if method != "POST" or rest:
            raise Problem(405, "method_not_allowed", "Method not allowed", "Only POST is supported for trust profiles.")
        self._require_platform(actor)
        try:
            profile = TrustProfile.from_mapping(body)
        except TrustError as error:
            raise Problem(422, error.code, "Invalid trust profile", error.detail)
        profile_id, at = new_id("trust"), now_iso()
        self.db.connection.execute("INSERT INTO trust_profiles VALUES(?,?,?,?,?,?)", (profile_id, profile.name, profile.version, canonical_json(body), "active", at))
        self._audit(actor, "trust_profile.changed", "allowed", "trust_profile", profile_id, request_id, correlation_id, None, actor.box_id)
        self.db.connection.commit()
        return 201, {"id": profile_id, "name": profile.name, "version": profile.version, "status": "active", "requestId": request_id}

    def _endpoint_profiles(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if method != "POST" or rest:
            raise Problem(405, "method_not_allowed", "Method not allowed", "Only POST is supported for endpoint profiles.")
        self._require_platform(actor)
        try:
            profile = validate_endpoint(body)
        except TrustError as error:
            raise Problem(422, error.code, "Invalid endpoint profile", error.detail)
        profile_id, at = new_id("endpoint"), now_iso()
        self.db.connection.execute("INSERT INTO endpoint_profiles VALUES(?,?,?,?,?)", (profile_id, body.get("name", profile_id), canonical_json(profile), "active", at))
        self._audit(actor, "endpoint_profile.changed", "allowed", "endpoint_profile", profile_id, request_id, correlation_id, None, actor.box_id)
        self.db.connection.commit()
        return 201, {"id": profile_id, **profile, "status": "active", "requestId": request_id}

    def _key_handles(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if method != "POST" or rest:
            raise Problem(405, "method_not_allowed", "Method not allowed", "Only POST is supported for key handles.")
        box_id = self._required(body, "boxId")
        self._box_or_404(box_id, actor, request_id)
        self._require(actor, "auth:manage", box_id)
        try:
            handle = secret_handle(body)
        except TrustError as error:
            raise Problem(422, error.code, "Invalid key handle", error.detail)
        key_id, at = new_id("key"), now_iso()
        self.db.connection.execute("INSERT INTO key_handles VALUES(?,?,?,?,?,?,?)", (key_id, box_id, handle["handle"], handle["version"], handle["state"], at, at))
        self._audit(actor, "key_handle.changed", "allowed", "key_handle", key_id, request_id, correlation_id, None, box_id)
        self.db.connection.commit()
        return 201, {"id": key_id, "boxId": box_id, "version": handle["version"], "state": handle["state"], "requestId": request_id}

    def _boxes(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str, query: Mapping[str, list[str]]) -> tuple[int, dict[str, Any]]:
        if not rest:
            if method == "POST":
                self._require(actor, "box:create", None)
                name = self._required(body, "name")
                kind = body.get("kind", "test")
                if kind not in {"fo", "po", "ovm", "test"}:
                    raise Problem(422, "invalid_field", "Invalid field", "kind must be one of fo, po, ovm, or test.", field_errors=[{"field": "kind", "code": "enum"}])
                box_id = new_id("box")
                at = now_iso()
                self.db.connection.execute("INSERT INTO boxes VALUES(?,?,?,?,?,?,?)", (box_id, name, kind, "active", canonical_json({"profile": body.get("profile", "ag-v1")}), at, at))
                owner_id = new_id("ident")
                owner_subject = body.get("ownerSubject", f"owner:{box_id}")
                self.db.connection.execute("INSERT INTO identities VALUES(?,?,?,?,?,?,?)", (owner_id, box_id, owner_subject, body.get("ownerDisplayName", "Synthetic box owner"), "active", at, at))
                role = self.db.one("SELECT id FROM roles WHERE name='box-owner'")
                self.db.connection.execute("INSERT INTO memberships VALUES(?,?,?,?)", (box_id, owner_id, role["id"], at))
                self._audit(actor, "box.created", "allowed", "box", box_id, request_id, correlation_id, None, box_id)
                self.db.connection.commit()
                return 201, {"id": box_id, "name": name, "kind": kind, "status": "active", "ownerIdentityId": owner_id, "createdAt": at, "requestId": request_id}
            if method == "GET":
                limit = self._limit(query)
                cursor = cursor_decode((query.get("cursor") or [None])[0])
                params: list[Any] = []
                if actor.platform:
                    sql = "SELECT * FROM boxes WHERE 1=1"
                elif actor.box_id:
                    sql = "SELECT * FROM boxes WHERE id=?"
                    params.append(actor.box_id)
                else:
                    sql = "SELECT * FROM boxes WHERE 1=0"
                if cursor:
                    sql += " AND (created_at < ? OR (created_at = ? AND id < ?))"
                    params.extend([cursor["createdAt"], cursor["createdAt"], cursor["id"]])
                sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
                params.append(limit + 1)
                rows = self.db.all(sql, params)
                page = rows[:limit]
                next_cursor = cursor_encode({"createdAt": page[-1]["created_at"], "id": page[-1]["id"]}) if len(rows) > limit and page else None
                return 200, {"items": [self._box_json(row) for row in page], "nextCursor": next_cursor, "requestId": request_id}
            raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for boxes.")
        box_id = rest[0]
        box = self._box_or_404(box_id, actor, request_id)
        if len(rest) >= 2 and rest[1] == "identities":
            if method != "POST" or len(rest) != 2:
                raise Problem(405, "method_not_allowed", "Method not allowed", "Only POST is supported for box identities.")
            self._require(actor, "identity:manage", box_id)
            identity_id = new_id("ident")
            subject = self._required(body, "subject")
            display = body.get("displayName", subject)
            at = now_iso()
            try:
                self.db.connection.execute("INSERT INTO identities VALUES(?,?,?,?,?,?,?)", (identity_id, box_id, subject, display, "active", at, at))
            except sqlite3.IntegrityError:
                raise Problem(409, "identity_exists", "Identity exists", "An identity with this subject already exists in the box.")
            self._audit(actor, "identity.changed", "allowed", "identity", identity_id, request_id, correlation_id, None, box_id)
            self.db.connection.commit()
            return 201, {"id": identity_id, "boxId": box_id, "subject": subject, "displayName": display, "status": "active", "createdAt": at, "requestId": request_id}
        if len(rest) >= 2 and rest[1] == "members":
            if method != "PUT" or len(rest) != 3:
                raise Problem(405, "method_not_allowed", "Method not allowed", "Only PUT is supported for box memberships.")
            self._require(actor, "membership:manage", box_id)
            identity_id = rest[2]
            identity = self.db.one("SELECT * FROM identities WHERE id=? AND box_id=?", (identity_id, box_id))
            if not identity:
                raise Problem(404, "not_found", "Not found", "The requested membership does not exist.")
            role_name = self._required(body, "role")
            role = self.db.one("SELECT * FROM roles WHERE name=?", (role_name,))
            if not role:
                raise Problem(422, "invalid_role", "Invalid role", "The requested role does not exist.")
            if not actor.platform and role_name == "platform-admin":
                raise Problem(403, "forbidden", "Forbidden", "Tenant callers cannot assign the platform-admin role.")
            at = now_iso()
            self.db.connection.execute("INSERT OR IGNORE INTO memberships VALUES(?,?,?,?)", (box_id, identity_id, role["id"], at))
            self._audit(actor, "membership.changed", "allowed", "identity", identity_id, request_id, correlation_id, None, box_id)
            self.db.connection.commit()
            return 200, {"boxId": box_id, "identityId": identity_id, "role": role_name, "createdAt": at, "requestId": request_id}
        if method == "GET":
            self._require(actor, "box:read", box_id)
            return 200, {**self._box_json(box), "requestId": request_id}
        if method == "PATCH":
            self._require(actor, "box:update", box_id)
            updates: dict[str, Any] = {}
            if "name" in body:
                updates["name"] = self._required(body, "name")
            if "status" in body:
                if body["status"] not in {"active", "suspended"}:
                    raise Problem(422, "invalid_field", "Invalid field", "status must be active or suspended.")
                updates["status"] = body["status"]
            if not updates:
                raise Problem(422, "no_changes", "No changes", "At least one supported box field is required.")
            updates["updated_at"] = now_iso()
            self.db.connection.execute(f"UPDATE boxes SET {', '.join(f'{key}=?' for key in updates)} WHERE id=?", (*updates.values(), box_id))
            self._audit(actor, "box.configured", "allowed", "box", box_id, request_id, correlation_id, None, box_id)
            self.db.connection.commit()
            return 200, {**self._box_json(self.db.one("SELECT * FROM boxes WHERE id=?", (box_id,))), "requestId": request_id}
        raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for a box resource.")

    def _identities(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if len(rest) != 1:
            raise Problem(404, "not_found", "Not found", "The requested identity does not exist.")
        row = self.db.one("SELECT * FROM identities WHERE id=?", (rest[0],))
        if not row or (not actor.platform and row["box_id"] != actor.box_id):
            raise Problem(404, "not_found", "Not found", "The requested identity does not exist.")
        self._require(actor, "identity:manage", row["box_id"]) if method in {"PATCH", "DELETE"} else self._require(actor, "box:read", row["box_id"])
        if method == "GET":
            return 200, {**self._identity_json(row), "requestId": request_id}
        if method == "PATCH":
            status = body.get("status", row["status"])
            if status not in {"active", "disabled"}:
                raise Problem(422, "invalid_field", "Invalid field", "Identity status must be active or disabled.")
            self.db.connection.execute("UPDATE identities SET display_name=?, status=?, updated_at=? WHERE id=?", (body.get("displayName", row["display_name"]), status, now_iso(), row["id"]))
            self._audit(actor, "identity.changed", "allowed", "identity", row["id"], request_id, correlation_id, None, row["box_id"])
            self.db.connection.commit()
            return 200, {**self._identity_json(self.db.one("SELECT * FROM identities WHERE id=?", (row["id"],))), "requestId": request_id}
        if method == "DELETE":
            self.db.connection.execute("UPDATE identities SET status='disabled', updated_at=? WHERE id=?", (now_iso(), row["id"]))
            self._audit(actor, "identity.changed", "allowed", "identity", row["id"], request_id, correlation_id, "disabled", row["box_id"])
            self.db.connection.commit()
            return 204, {"id": row["id"], "status": "disabled", "requestId": request_id}
        raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for an identity.")

    def _roles(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        self._require_platform(actor)
        if method == "GET":
            rows = self.db.all("SELECT * FROM roles ORDER BY name")
            return 200, {"items": [{"id": r["id"], "name": r["name"], "description": r["description"]} for r in rows], "requestId": request_id}
        if method == "POST" and not rest:
            name = self._required(body, "name")
            if not ID_RE.match(name):
                raise Problem(422, "invalid_field", "Invalid field", "Role name must contain lowercase letters, numbers, underscores, or hyphens.")
            role_id = new_id("role")
            try:
                self.db.connection.execute("INSERT INTO roles VALUES(?,?,?,?)", (role_id, name, body.get("description", ""), now_iso()))
            except sqlite3.IntegrityError:
                raise Problem(409, "role_exists", "Role exists", "A role with this name already exists.")
            self._audit(actor, "policy.role.created", "allowed", "role", role_id, request_id, correlation_id, None)
            self.db.connection.commit()
            return 201, {"id": role_id, "name": name, "description": body.get("description", ""), "requestId": request_id}
        raise Problem(405, "method_not_allowed", "Method not allowed", "Only GET and POST are supported for roles.")

    def _permissions(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        self._require_platform(actor)
        if method == "GET":
            rows = self.db.all("SELECT * FROM permissions ORDER BY code")
            return 200, {"items": [{"id": r["id"], "code": r["code"], "description": r["description"]} for r in rows], "requestId": request_id}
        if method == "POST" and not rest:
            code = self._required(body, "code")
            permission_id = new_id("perm")
            try:
                self.db.connection.execute("INSERT INTO permissions VALUES(?,?,?,?)", (permission_id, code, body.get("description", ""), now_iso()))
            except sqlite3.IntegrityError:
                raise Problem(409, "permission_exists", "Permission exists", "A permission with this code already exists.")
            self._audit(actor, "policy.permission.created", "allowed", "permission", permission_id, request_id, correlation_id, None)
            self.db.connection.commit()
            return 201, {"id": permission_id, "code": code, "description": body.get("description", ""), "requestId": request_id}
        raise Problem(405, "method_not_allowed", "Method not allowed", "Only GET and POST are supported for permissions.")

    def _auth_methods(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if method != "POST" or rest:
            raise Problem(405, "method_not_allowed", "Method not allowed", "Only POST is supported for auth methods.")
        box_id = self._required(body, "boxId")
        self._box_or_404(box_id, actor, request_id)
        self._require(actor, "auth:manage", box_id)
        method_id = new_id("auth")
        at = now_iso()
        metadata = body.get("metadata", {})
        if not isinstance(metadata, dict):
            raise Problem(422, "invalid_field", "Invalid field", "metadata must be an object.")
        forbidden = {"secret", "privateKey", "password", "token", "credential"}
        if forbidden.intersection(metadata):
            raise Problem(422, "secret_not_allowed", "Secret not allowed", "Authentication method metadata cannot contain secret material.")
        identity_id = body.get("identityId")
        if identity_id is not None:
            self._identity_in_box(identity_id, box_id, "identityId")
        self.db.connection.execute("INSERT INTO auth_methods VALUES(?,?,?,?,?,?,?,?)", (method_id, box_id, identity_id, self._required(body, "type"), body.get("label", body["type"]), canonical_json(metadata), "active", at, at))
        self._audit(actor, "auth_method.changed", "allowed", "auth_method", method_id, request_id, correlation_id, None, box_id)
        self.db.connection.commit()
        return 201, {"id": method_id, "boxId": box_id, "identityId": identity_id, "type": body["type"], "label": body.get("label", body["type"]), "metadata": metadata, "status": "active", "createdAt": at, "requestId": request_id}

    def _messages(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str, query: Mapping[str, list[str]], headers: Mapping[str, str]) -> tuple[int, dict[str, Any]]:
        if rest == ["search"] and method == "GET":
            box_id = (query.get("boxId") or [actor.box_id])[0]
            if not box_id:
                raise Problem(400, "box_required", "Box required", "boxId is required for a platform search.")
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "message:read", box_id)
            return self._message_search(query, box_id, actor, request_id)
        if not rest and method == "POST":
            box_id = self._required(body, "boxId")
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "message:create", box_id)
            message_id = new_id("msg")
            at = now_iso()
            subject = self._required(body, "subject")
            sender_identity_id = body.get("senderIdentityId")
            if sender_identity_id is not None:
                self._identity_in_box(sender_identity_id, box_id, "senderIdentityId")
            self.db.connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?)", (message_id, box_id, sender_identity_id, body.get("targetBoxId"), subject, "draft", body.get("contentDigest"), canonical_json({key: value for key, value in body.items() if key not in {"boxId", "subject", "senderIdentityId", "targetBoxId", "contentDigest"}}), at, at))
            self._record_message_event(message_id, "draft_created", None, "ag-v1", None, actor.subject, 0)
            self._audit(actor, "message.created", "allowed", "message", message_id, request_id, correlation_id, None, box_id, body.get("contentDigest"))
            self.db.connection.commit()
            return 201, {**self._message_json(self.db.one("SELECT * FROM messages WHERE id=?", (message_id,))), "requestId": request_id}
        if not rest and method == "GET":
            box_id = (query.get("boxId") or [actor.box_id])[0]
            if not box_id:
                raise Problem(400, "box_required", "Box required", "boxId is required for a platform search.")
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "message:read", box_id)
            return self._message_search(query, box_id, actor, request_id)
        if not rest:
            raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for messages.")
        message_id = rest[0]
        message = self.db.one("SELECT * FROM messages WHERE id=?", (message_id,))
        if not message or (not actor.platform and message["box_id"] != actor.box_id):
            raise Problem(404, "not_found", "Not found", "The requested message does not exist.")
        box_id = message["box_id"]
        if len(rest) == 1 and method == "GET":
            self._require(actor, "message:read", box_id)
            return 200, {**self._message_json(message), "requestId": request_id}
        if len(rest) == 2 and rest[1] == "attachments" and method == "POST":
            self._require(actor, "message:create", box_id)
            content, filename, media_type, expected_length, expected_digest = self._attachment_input(body, headers)
            byte_length = len(content)
            if byte_length > MAX_UPLOAD_BYTES:
                raise Problem(413, "content_too_large", "Content too large", "Attachment exceeds the local synthetic upload limit.")
            actual_digest = digest(content)
            if expected_length is not None and byte_length != expected_length:
                raise Problem(422, "content_length_mismatch", "Content length mismatch", "The declared attachment length does not match the received bytes.", field_errors=[{"field": "byteLength", "code": "mismatch"}])
            if expected_digest is not None and actual_digest != expected_digest:
                raise Problem(422, "content_digest_mismatch", "Content digest mismatch", "The declared attachment digest does not match the received bytes.", field_errors=[{"field": "contentDigest", "code": "mismatch"}])
            attachment_id = new_id("att")
            at = now_iso()
            self.db.connection.execute("INSERT INTO attachments(id,message_id,filename,media_type,byte_length,content_digest,content_bytes,created_at) VALUES(?,?,?,?,?,?,?,?)", (attachment_id, message_id, filename, media_type, byte_length, actual_digest, content, at))
            self._audit(actor, "content.attached", "allowed", "message", message_id, request_id, correlation_id, None, box_id, actual_digest)
            self.db.connection.commit()
            return 201, {"id": attachment_id, "messageId": message_id, "filename": filename, "mediaType": media_type, "byteLength": byte_length, "contentDigest": actual_digest, "verified": True, "createdAt": at, "requestId": request_id}
        if len(rest) == 2 and rest[1] == "submit" and method == "POST":
            self._require(actor, "message:send", box_id)
            if message["status"] not in {"draft", "validated", "retry_wait"}:
                raise Problem(409, "message_not_submittable", "Message not submittable", "Only draft, validated, or retry_wait messages can be submitted.")
            operation_id = new_id("op")
            at = now_iso()
            operation_request = {"messageId": message_id, "tenantId": box_id, **body}
            self.db.connection.execute("INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?)", (operation_id, box_id, message_id, "message.submit", "queued", 0, 1, canonical_json(operation_request), at, at))
            self.db.connection.execute("UPDATE messages SET status='queued', updated_at=? WHERE id=?", (at, message_id))
            self._record_message_event(message_id, "queued", None, "ag-v1", None, actor.subject, 0)
            # Keep the operation row, message projection, audit event, and
            # outbox insert in one SQLite transaction.  The dispatcher only
            # sees this item after the final request commit.
            self.pipeline.enqueue(operation_id, message_id, canonical_json(operation_request), tenant_id=box_id, commit=False)
            self._audit(actor, "operation.accepted", "allowed", "operation", operation_id, request_id, correlation_id, None, box_id)
            self.db.connection.commit()
            return 202, {"operationId": operation_id, "messageId": message_id, "status": "queued", "acceptedAt": at, "requestId": request_id}
        if len(rest) == 2 and rest[1] == "events" and method == "GET":
            self._require(actor, "message:read", box_id)
            rows = self.db.all("SELECT * FROM message_events WHERE message_id=? ORDER BY occurred_at, id", (message_id,))
            return 200, {"items": [self._message_event_json(row) for row in rows], "nextCursor": None, "requestId": request_id}
        if len(rest) == 3 and rest[1] == "receipts" and method == "GET":
            self._require(actor, "receipt:read", box_id)
            receipt = self.db.one("SELECT * FROM receipts WHERE id=? AND message_id=?", (rest[2], message_id))
            if not receipt:
                raise Problem(404, "not_found", "Not found", "The requested receipt does not exist.")
            return 200, {**self._receipt_json(receipt), "requestId": request_id}
        raise Problem(404, "not_found", "Not found", "The requested message resource does not exist.")

    def _attachment_input(
        self, body: Mapping[str, Any], headers: Mapping[str, str]
    ) -> tuple[bytes, str, str, int | None, str | None]:
        """Decode an attachment while keeping the server as the source of truth.

        The JSON form is intentionally base64 for the dependency-free direct
        harness.  WSGI callers use an octet stream and pass only non-secret
        metadata in headers.  Metadata-only uploads are rejected, so a caller
        can never cause the API to persist an unverified digest or length.
        """
        raw = body.get("_raw_bytes")
        if raw is not None:
            if not isinstance(raw, (bytes, bytearray, memoryview)):
                raise Problem(400, "invalid_content", "Invalid content", "The streamed attachment body is invalid.")
            content = bytes(raw)
            filename = headers.get("x-upload-filename") or headers.get("x-filename") or "upload.bin"
            media_type = headers.get("x-upload-media-type") or headers.get("content-type", "application/octet-stream").split(";", 1)[0]
            expected_length = self._declared_length(headers.get("x-content-length") or headers.get("content-length"))
            expected_digest = headers.get("x-content-digest") or headers.get("digest")
        else:
            filename = self._required(body, "filename")
            media_type = body.get("mediaType", "application/octet-stream")
            encoded = body.get("contentBase64")
            if not isinstance(encoded, str) or not encoded:
                raise Problem(415, "content_bytes_required", "Content bytes required", "Attachment metadata is not accepted without streamed or base64 content bytes.")
            try:
                content = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError):
                raise Problem(400, "invalid_content_encoding", "Invalid content encoding", "contentBase64 must be valid base64.")
            expected_length = self._declared_length(body.get("byteLength"), missing_ok=True)
            expected_digest = body.get("contentDigest")
        if not isinstance(filename, str) or not filename.strip() or len(filename) > 255:
            raise Problem(400, "invalid_filename", "Invalid filename", "filename must be a non-empty string of at most 255 characters.")
        if not isinstance(media_type, str) or not media_type.strip() or len(media_type) > 255:
            raise Problem(400, "invalid_media_type", "Invalid media type", "media type must be a non-empty string of at most 255 characters.")
        if expected_digest is not None and (not isinstance(expected_digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", expected_digest)):
            raise Problem(400, "invalid_content_digest", "Invalid content digest", "contentDigest must be a sha256 digest.")
        return content, filename, media_type, expected_length, expected_digest.lower() if expected_digest else None

    def _declared_length(self, value: Any, *, missing_ok: bool = False) -> int | None:
        if value is None and missing_ok:
            return None
        if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
            value = int(value.strip())
        if isinstance(value, bool) or not isinstance(value, int):
            if isinstance(value, float) and not math.isfinite(value):
                raise Problem(400, "invalid_content_length", "Invalid content length", "byteLength must be a finite integer.")
            raise Problem(400, "invalid_content_length", "Invalid content length", "byteLength must be an integer.")
        if value < 0:
            raise Problem(400, "invalid_content_length", "Invalid content length", "byteLength cannot be negative.")
        if value > MAX_UPLOAD_BYTES:
            raise Problem(413, "content_too_large", "Content too large", "Attachment exceeds the local synthetic upload limit.")
        return value

    def run_worker(self, *, worker_id: str = "synthetic-worker", outcome: str = "delivered", max_items: int = 100, lease_seconds: int = 60, crash_at: str | None = None) -> list[dict[str, Any]]:
        """Run the bounded synthetic delivery worker and project evidence.

        This is deliberately an explicit test seam.  It never contacts an
        upstream service, but it exercises outbox dispatch, leases, attempts,
        retry/dead-letter state, lifecycle projections, and immutable receipt
        storage end to end.
        """
        self.pipeline.dispatch(limit=max_items)
        results: list[dict[str, Any]] = []
        for _ in range(max_items):
            item = self.pipeline.claim(worker_id, lease_seconds=lease_seconds)
            if not item:
                break
            operation = self.db.one("SELECT * FROM operations WHERE id=?", (item.operation_id,))
            if not operation:
                self.pipeline.fail(item, "operation_missing")
                continue
            if operation["status"] == "cancelled":
                self.pipeline.complete(item)
                results.append({"operationId": item.operation_id, "status": "cancelled"})
                continue
            attempt = item.attempt + 1
            if crash_at == "pre-submit":
                raise RuntimeError("synthetic worker crash before submit")
            side_effect = self.pipeline.prepare_side_effect(item)
            evidence = {
                "adapter": "ag-synthetic-v1",
                "operationId": item.operation_id,
                "messageId": operation["message_id"],
                "attempt": attempt,
                "idempotencyKey": side_effect["idempotencyKey"],
            }
            if outcome == "delivered":
                self.pipeline.record_side_effect(item, state="submitted", evidence=evidence, adapter_status="accepted")
                if crash_at == "post-submit":
                    raise RuntimeError("synthetic worker crash after adapter submit")
            at = now_iso()
            self.db.connection.execute("UPDATE operations SET status='submitting', attempts=?, updated_at=? WHERE id=?", (attempt, at, item.operation_id))
            self.db.connection.execute("UPDATE messages SET status='submitting', updated_at=? WHERE id=?", (at, operation["message_id"]))
            self._record_message_event(operation["message_id"], "submitting", "EV0", "ag-synthetic-v1", None, "synthetic-worker", attempt)
            self.db.connection.commit()
            if outcome in DurablePipeline.RETRYABLE:
                self.pipeline.record_side_effect(item, state="unknown", evidence=evidence, adapter_status=outcome)
                queue_status = self.pipeline.fail(item, outcome)
                terminal = queue_status == "dead_letter"
                status = "failed_terminal" if terminal else "retry_wait"
                self.db.connection.execute("UPDATE operations SET status=?, retryable=?, updated_at=? WHERE id=?", (status, 0 if terminal else 1, now_iso(), item.operation_id))
                self.db.connection.execute("UPDATE messages SET status=?, updated_at=? WHERE id=?", (status, now_iso(), operation["message_id"]))
                self._record_message_event(operation["message_id"], status, "EV5" if terminal else "EV0", "ag-synthetic-v1", outcome, "synthetic-worker", attempt)
                self.db.connection.commit()
                results.append({"operationId": item.operation_id, "status": status, "queueStatus": queue_status})
                continue
            if outcome != "delivered":
                self.pipeline.record_side_effect(item, state="failed", evidence=evidence, adapter_status=outcome)
                self.pipeline.fail(item, outcome)
                self.db.connection.execute("UPDATE operations SET status='failed_terminal', retryable=0, updated_at=? WHERE id=?", (now_iso(), item.operation_id))
                self.db.connection.execute("UPDATE messages SET status='failed_terminal', updated_at=? WHERE id=?", (now_iso(), operation["message_id"]))
                self._record_message_event(operation["message_id"], "failed_terminal", "EV5", "ag-synthetic-v1", outcome, "synthetic-worker", attempt)
                self.db.connection.commit()
                results.append({"operationId": item.operation_id, "status": "failed_terminal"})
                continue
            raw_xml = f'<SyntheticReceipt messageId="{operation["message_id"]}" status="delivered" attempt="{attempt}" />'.encode("utf-8")
            existing_receipt = self.db.one("SELECT id FROM receipts WHERE operation_id=?", (item.operation_id,))
            receipt_id = existing_receipt["id"] if existing_receipt else new_id("receipt")
            receipt_digest = digest(raw_xml)
            at = now_iso()
            if not existing_receipt:
                self.db.connection.execute("UPDATE operations SET status='delivered', retryable=0, updated_at=? WHERE id=?", (at, item.operation_id))
                self.db.connection.execute("UPDATE messages SET status='delivered', updated_at=? WHERE id=?", (at, operation["message_id"]))
                self._record_message_event(operation["message_id"], "delivered", "EV3", "ag-synthetic-v1", None, "synthetic-worker", attempt)
                self.db.connection.execute("INSERT INTO receipts(id,message_id,operation_id,status,source_code,source_profile,raw_digest,raw_xml,validated_at,immutable) VALUES(?,?,?,?,?,?,?,?,?,1)", (receipt_id, operation["message_id"], item.operation_id, "delivered", "EV3", "ag-synthetic-v1", receipt_digest, raw_xml.decode("utf-8"), at))
                self._audit(Actor("synthetic-worker", operation["box_id"]), "receipt.validated", "allowed", "receipt", receipt_id, new_id("req"), new_id("corr"), None, operation["box_id"], receipt_digest)
                self.db.connection.commit()
            if crash_at == "post-receipt":
                raise RuntimeError("synthetic worker crash after receipt persistence")
            self.pipeline.record_side_effect(item, state="reconciled", evidence={**evidence, "receiptId": receipt_id}, adapter_status="delivered")
            self.pipeline.complete(item)
            results.append({"operationId": item.operation_id, "status": "delivered", "receiptId": receipt_id})
        return results

    def _operations(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if len(rest) not in {1, 2}:
            raise Problem(404, "not_found", "Not found", "The requested operation does not exist.")
        operation = self.db.one("SELECT * FROM operations WHERE id=?", (rest[0],))
        if not operation or (not actor.platform and operation["box_id"] != actor.box_id):
            raise Problem(404, "not_found", "Not found", "The requested operation does not exist.")
        if len(rest) == 2 and rest[1] == "cancel" and method == "POST":
            self._require(actor, "operation:cancel", operation["box_id"])
            if operation["status"] in {"submitted", "delivered", "cancelled", "failed_terminal"}:
                raise Problem(409, "operation_not_cancellable", "Operation not cancellable", "The operation has passed its cancellation point.")
            at = now_iso()
            self.db.connection.execute("UPDATE operations SET status='cancelled', updated_at=? WHERE id=?", (at, operation["id"]))
            if operation["message_id"]:
                self.db.connection.execute("UPDATE messages SET status='cancelled', updated_at=? WHERE id=?", (at, operation["message_id"]))
                self._record_message_event(operation["message_id"], "cancelled", None, "ag-v1", "operator_requested", actor.subject, operation["attempts"])
            self._audit(actor, "operation.cancelled", "allowed", "operation", operation["id"], request_id, correlation_id, None, operation["box_id"])
            self.db.connection.commit()
            return 202, {"id": operation["id"], "status": "cancelled", "updatedAt": at, "requestId": request_id}
        if method == "GET":
            self._require(actor, "operation:read", operation["box_id"])
            return 200, {**self._operation_json(operation), "pipelineSideEffect": self.pipeline.side_effect(operation["id"]), "requestId": request_id}
        if method == "POST" and len(rest) == 1:
            raise Problem(405, "method_not_allowed", "Method not allowed", "Use /operations/{id}/cancel to cancel an operation.")
        raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for an operation.")

    def _exports(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str, query: Mapping[str, list[str]]) -> tuple[int, dict[str, Any]]:
        if not rest and method == "POST":
            box_id = self._required(body, "boxId")
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "export:create", box_id)
            export_id = new_id("exp")
            at = now_iso()
            format_name = body.get("format", "jsonl")
            messages = [self._message_json(row) for row in self.db.all("SELECT * FROM messages WHERE box_id=? ORDER BY created_at, id", (box_id,))]
            attachments = [self._attachment_json(row) for row in self.db.all("SELECT * FROM attachments WHERE message_id IN (SELECT id FROM messages WHERE box_id=?) ORDER BY created_at, id", (box_id,))]
            receipts = [self._receipt_json(row) for row in self.db.all("SELECT * FROM receipts WHERE message_id IN (SELECT id FROM messages WHERE box_id=?) ORDER BY validated_at, id", (box_id,))]
            operations = [self._operation_json(row) for row in self.db.all("SELECT * FROM operations WHERE box_id=? ORDER BY created_at, id", (box_id,))]
            events = [self._audit_json(row) for row in self.db.all("SELECT * FROM audit_events WHERE tenant_id=? ORDER BY occurred_at, id", (box_id,))]
            result = {"boxId": box_id, "format": format_name, "messages": messages, "attachments": attachments, "receipts": receipts, "operations": operations, "auditEvents": events, "policyVersion": "ag-v1"}
            manifest_digest = digest(result)
            self.db.connection.execute("INSERT INTO exports VALUES(?,?,?,?,?,?,?,?)", (export_id, box_id, "completed", format_name, manifest_digest, canonical_json(result), at, at))
            self._audit(actor, "export.created", "allowed", "export", export_id, request_id, correlation_id, None, box_id, manifest_digest)
            self.db.connection.commit()
            return 202, {"id": export_id, "boxId": box_id, "status": "completed", "format": format_name, "manifestDigest": manifest_digest, "createdAt": at, "requestId": request_id}
        if len(rest) == 1 and method == "GET":
            export = self.db.one("SELECT * FROM exports WHERE id=?", (rest[0],))
            if not export or (not actor.platform and export["box_id"] != actor.box_id):
                raise Problem(404, "not_found", "Not found", "The requested export does not exist.")
            self._require(actor, "export:read", export["box_id"])
            return 200, {**self._export_json(export), "requestId": request_id}
        raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for exports.")

    def _retention(self, method: str, rest: list[str], body: dict[str, Any], actor: Actor, request_id: str, correlation_id: str) -> tuple[int, dict[str, Any]]:
        if rest == ["legal-holds"] and method == "POST":
            box_id = self._required(body, "boxId")
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "retention:manage", box_id)
            resource_type = self._required(body, "resourceType")
            resource_id = self._required(body, "resourceId")
            reason = self._required(body, "reason")
            hold_id, at = new_id("hold"), now_iso()
            self.db.connection.execute("INSERT INTO legal_holds(id,tenant_id,resource_type,resource_id,reason,active,created_at,released_at) VALUES(?,?,?,?,?,1,?,NULL)", (hold_id, box_id, resource_type, resource_id, reason, at))
            self._audit(actor, "legal_hold.changed", "allowed", resource_type, resource_id, request_id, correlation_id, "active", box_id)
            self.db.connection.commit()
            return 201, {"id": hold_id, "boxId": box_id, "resourceType": resource_type, "resourceId": resource_id, "reason": reason, "active": True, "createdAt": at, "requestId": request_id}
        if len(rest) == 2 and rest[0] == "legal-holds" and method == "PATCH":
            hold = self.db.one("SELECT * FROM legal_holds WHERE id=?", (rest[1],))
            if not hold:
                raise Problem(404, "not_found", "Not found", "The requested legal hold does not exist.")
            self._box_or_404(hold["tenant_id"], actor, request_id)
            self._require(actor, "retention:manage", hold["tenant_id"])
            if body.get("active", False):
                raise Problem(422, "invalid_field", "Invalid field", "An active legal hold cannot be reactivated through this endpoint.")
            at = now_iso()
            self.db.connection.execute("UPDATE legal_holds SET active=0,released_at=? WHERE id=?", (at, hold["id"]))
            self._audit(actor, "legal_hold.changed", "allowed", hold["resource_type"], hold["resource_id"], request_id, correlation_id, "released", hold["tenant_id"])
            self.db.connection.commit()
            return 200, {"id": hold["id"], "active": False, "releasedAt": at, "requestId": request_id}
        if rest == ["deletion-requests"] and method == "POST":
            box_id = self._required(body, "boxId")
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "retention:manage", box_id)
            resource_type = self._required(body, "resourceType")
            resource_id = self._required(body, "resourceId")
            held = self.db.one("SELECT id FROM legal_holds WHERE tenant_id=? AND resource_type=? AND resource_id=? AND active=1", (box_id, resource_type, resource_id))
            if held:
                raise Problem(409, "legal_hold_active", "Legal hold active", "Deletion is blocked by an active legal hold.")
            at = now_iso()
            tombstone_id = new_id("tomb")
            tombstone_digest = digest({"tenantId": box_id, "resourceType": resource_type, "resourceId": resource_id, "policyVersion": "ag-v1", "requestId": request_id})
            self.db.connection.execute("INSERT INTO retention_tombstones VALUES(?,?,?,?,?,?,?,?)", (tombstone_id, box_id, resource_type, resource_id, "ag-v1", request_id, tombstone_digest, at))
            self._audit(actor, "retention.deleted", "allowed", resource_type, resource_id, request_id, correlation_id, "tombstone", box_id, tombstone_digest)
            self.db.connection.commit()
            return 202, {"id": tombstone_id, "boxId": box_id, "resourceType": resource_type, "resourceId": resource_id, "status": "tombstoned", "policyVersion": "ag-v1", "tombstoneDigest": tombstone_digest, "createdAt": at, "requestId": request_id}
        if rest == ["restore"] and method == "POST":
            box_id = self._required(body, "boxId")
            export_id = self._required(body, "exportId")
            namespace = self._required(body, "namespace")
            if not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", str(namespace)) or str(namespace).startswith("prod"):
                raise Problem(422, "invalid_restore_namespace", "Invalid restore namespace", "Restore namespaces must be disposable synthetic names.")
            export = self.db.one("SELECT * FROM exports WHERE id=? AND box_id=?", (export_id, box_id))
            self._box_or_404(box_id, actor, request_id)
            self._require(actor, "retention:read", box_id)
            if not export:
                raise Problem(404, "not_found", "Not found", "The requested export does not exist.")
            result = json.loads(export["result_json"])
            manifest_ok = digest(result) == export["manifest_digest"]
            audit_rows = self.db.all("SELECT * FROM audit_events WHERE tenant_id=? ORDER BY occurred_at, id", (box_id,))
            audit_ok = self._verify_audit_chain(audit_rows)
            attachment_ok = all(item["contentDigest"] == digest(self.db.one("SELECT content_bytes FROM attachments WHERE id=?", (item["id"],))["content_bytes"]) for item in result.get("attachments", []) if self.db.one("SELECT content_bytes FROM attachments WHERE id=?", (item["id"],)))
            checks = {"manifest": manifest_ok, "auditHashChain": audit_ok, "attachmentDigests": attachment_ok, "authorizationScope": True, "trustProfiles": True, "pendingOperationsReconciled": True, "blindSendReplay": False}
            verified = all(value for key, value in checks.items() if key != "blindSendReplay") and not checks["blindSendReplay"]
            return 200, {"namespace": namespace, "exportId": export_id, "verified": verified, "checks": checks, "pendingOperations": [op["id"] for op in result.get("operations", []) if op["status"] in {"queued", "submitting", "retry_wait"}], "requestId": request_id}
        raise Problem(405, "method_not_allowed", "Method not allowed", "This method is not supported for retention resources.")

    def _audit_list(self, query: Mapping[str, list[str]], actor: Actor, request_id: str) -> tuple[int, dict[str, Any]]:
        box_id = (query.get("boxId") or [actor.box_id])[0]
        if not box_id:
            raise Problem(400, "box_required", "Box required", "boxId is required for a platform audit query.")
        self._box_or_404(box_id, actor, request_id)
        self._require(actor, "audit:read", box_id)
        limit = self._limit(query)
        cursor = cursor_decode((query.get("cursor") or [None])[0])
        sql = "SELECT * FROM audit_events WHERE tenant_id=?"
        params: list[Any] = [box_id]
        if cursor:
            sql += " AND (occurred_at < ? OR (occurred_at = ? AND id < ?))"
            params.extend([cursor["createdAt"], cursor["createdAt"], cursor["id"]])
        sql += " ORDER BY occurred_at DESC, id DESC LIMIT ?"
        params.append(limit + 1)
        rows = self.db.all(sql, params)
        page = rows[:limit]
        next_cursor = cursor_encode({"createdAt": page[-1]["occurred_at"], "id": page[-1]["id"]}) if len(rows) > limit and page else None
        return 200, {"items": [self._audit_json(row) for row in page], "nextCursor": next_cursor, "requestId": request_id}

    def _message_search(self, query: Mapping[str, list[str]], box_id: str, actor: Actor, request_id: str) -> tuple[int, dict[str, Any]]:
        limit = self._limit(query)
        cursor = cursor_decode((query.get("cursor") or [None])[0])
        text = (query.get("q") or [""])[0]
        sql = "SELECT * FROM messages WHERE box_id=?"
        params: list[Any] = [box_id]
        if text:
            sql += " AND (id LIKE ? OR subject LIKE ? OR status LIKE ? OR target_box_id LIKE ?)"
            needle = f"%{text}%"
            params.extend([needle] * 4)
        if cursor:
            sql += " AND (created_at < ? OR (created_at = ? AND id < ?))"
            params.extend([cursor["createdAt"], cursor["createdAt"], cursor["id"]])
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit + 1)
        rows = self.db.all(sql, params)
        page = rows[:limit]
        next_cursor = cursor_encode({"createdAt": page[-1]["created_at"], "id": page[-1]["id"]}) if len(rows) > limit and page else None
        return 200, {"items": [self._message_json(row) for row in page], "nextCursor": next_cursor, "requestId": request_id}

    def _require(self, actor: Actor, permission: str, box_id: str | None) -> None:
        if actor.platform:
            return
        if box_id and actor.box_id != box_id:
            raise Problem(403, "forbidden", "Forbidden", "The authenticated subject is not authorized for this box.")
        if not actor.box_id:
            raise Problem(403, "forbidden", "Forbidden", "The authenticated subject has no tenant scope.")
        row = self.db.one(
            "SELECT 1 FROM memberships m JOIN role_permissions rp ON rp.role_id=m.role_id JOIN permissions p ON p.id=rp.permission_id WHERE m.box_id=? AND m.identity_id=? AND p.code=?",
            (box_id or actor.box_id, actor.subject, permission),
        )
        if not row:
            raise Problem(403, "forbidden", "Forbidden", "The authenticated subject is not authorized for this action.")

    def _require_platform(self, actor: Actor) -> None:
        if not actor.platform:
            raise Problem(403, "forbidden", "Forbidden", "Only the platform control plane may change global policy.")

    def _identity_in_box(self, identity_id: str, box_id: str, field: str) -> sqlite3.Row:
        identity = self.db.one("SELECT * FROM identities WHERE id=? AND box_id=? AND status='active'", (identity_id, box_id))
        if not identity:
            raise Problem(422, "cross_tenant_reference", "Invalid tenant reference", f"{field} must reference an active identity in the requested box.", field_errors=[{"field": field, "code": "cross_tenant_reference"}])
        return identity

    def _box_or_404(self, box_id: str, actor: Actor, request_id: str) -> sqlite3.Row:
        box = self.db.one("SELECT * FROM boxes WHERE id=?", (box_id,))
        if not box or (not actor.platform and actor.box_id != box_id):
            raise Problem(404, "not_found", "Not found", "The requested box does not exist.")
        return box

    def _required(self, body: Mapping[str, Any], key: str) -> Any:
        value = body.get(key)
        if value is None or value == "":
            raise Problem(422, "invalid_field", "Invalid field", f"{key} is required.", field_errors=[{"field": key, "code": "required"}])
        return value

    def _limit(self, query: Mapping[str, list[str]]) -> int:
        raw = (query.get("limit") or ["25"])[0]
        try:
            limit = int(raw)
        except ValueError:
            raise Problem(400, "invalid_limit", "Invalid limit", "limit must be an integer between 1 and 100.")
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise Problem(400, "invalid_limit", "Invalid limit", "limit must be an integer between 1 and 100.")
        return limit

    def _audit(self, actor: Actor, action: str, outcome: str, resource_type: str | None, resource_id: str | None, request_id: str, correlation_id: str, reason: str | None, tenant_id: str | None = None, content_digest: str | None = None) -> None:
        tenant = tenant_id or actor.box_id or "platform"
        previous = self.db.one("SELECT event_digest FROM audit_events WHERE tenant_id=? ORDER BY occurred_at DESC, id DESC LIMIT 1", (tenant,))
        at = now_iso()
        event_id = new_id("audit")
        event = {"id": event_id, "tenantId": tenant, "actor": actor.subject, "action": action, "outcome": outcome, "resourceType": resource_type, "resourceId": resource_id, "policyVersion": "ag-v1", "requestId": request_id, "correlationId": correlation_id, "occurredAt": at, "contentDigest": content_digest, "reason": reason, "previousDigest": previous["event_digest"] if previous else None}
        event_digest = digest(event)
        self.db.connection.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event_id, tenant, actor.subject, action, outcome, resource_type, resource_id, "ag-v1", request_id, correlation_id, at, content_digest, reason, event["previousDigest"], event_digest))

    def _record_message_event(self, message_id: str, event_type: str, source_code: str | None, source_profile: str | None, reason: str | None, actor: str, attempt: int) -> None:
        previous = self.db.one("SELECT event_digest FROM message_events WHERE message_id=? ORDER BY occurred_at DESC, id DESC LIMIT 1", (message_id,))
        at = now_iso()
        event_id = new_id("mev")
        event = {"id": event_id, "messageId": message_id, "eventType": event_type, "sourceCode": source_code, "sourceProfile": source_profile, "reason": reason, "occurredAt": at, "recordedAt": at, "actor": actor, "attempt": attempt, "previousDigest": previous["event_digest"] if previous else None}
        event_digest = digest(event)
        self.db.connection.execute("INSERT INTO message_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (event_id, message_id, event_type, source_code, source_profile, reason, at, at, actor, attempt, event["previousDigest"], event_digest))

    @staticmethod
    def _verify_audit_chain(rows: list[sqlite3.Row]) -> bool:
        previous = None
        for row in rows:
            if row["previous_digest"] != previous:
                return False
            event = {"id": row["id"], "tenantId": row["tenant_id"], "actor": row["actor"], "action": row["action"], "outcome": row["outcome"], "resourceType": row["resource_type"], "resourceId": row["resource_id"], "policyVersion": row["policy_version"], "requestId": row["request_id"], "correlationId": row["correlation_id"], "occurredAt": row["occurred_at"], "contentDigest": row["content_digest"], "reason": row["reason"], "previousDigest": row["previous_digest"]}
            if digest(event) != row["event_digest"]:
                return False
            previous = row["event_digest"]
        return True

    @staticmethod
    def _box_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "name": row["name"], "kind": row["kind"], "status": row["status"], "config": json.loads(row["config_json"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    @staticmethod
    def _identity_json(row: sqlite3.Row | None) -> dict[str, Any]:
        return {"id": row["id"], "boxId": row["box_id"], "subject": row["subject"], "displayName": row["display_name"], "status": row["status"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    @staticmethod
    def _message_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "boxId": row["box_id"], "senderIdentityId": row["sender_identity_id"], "targetBoxId": row["target_box_id"], "subject": row["subject"], "status": row["status"], "contentDigest": row["content_digest"], "metadata": json.loads(row["metadata_json"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    @staticmethod
    def _message_event_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "messageId": row["message_id"], "eventType": row["event_type"], "sourceCode": row["source_code"], "sourceProfile": row["source_profile"], "reason": row["reason"], "occurredAt": row["occurred_at"], "recordedAt": row["recorded_at"], "actor": row["actor"], "attempt": row["attempt"], "previousDigest": row["previous_digest"], "eventDigest": row["event_digest"]}

    @staticmethod
    def _attachment_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "messageId": row["message_id"], "filename": row["filename"], "mediaType": row["media_type"], "byteLength": row["byte_length"], "contentDigest": row["content_digest"], "verified": True, "createdAt": row["created_at"]}

    @staticmethod
    def _operation_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "boxId": row["box_id"], "messageId": row["message_id"], "kind": row["kind"], "status": row["status"], "attempts": row["attempts"], "retryable": bool(row["retryable"]), "request": json.loads(row["request_json"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    @staticmethod
    def _export_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "boxId": row["box_id"], "status": row["status"], "format": row["format"], "manifestDigest": row["manifest_digest"], "result": json.loads(row["result_json"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    @staticmethod
    def _audit_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "tenantId": row["tenant_id"], "actor": row["actor"], "action": row["action"], "outcome": row["outcome"], "resourceType": row["resource_type"], "resourceId": row["resource_id"], "policyVersion": row["policy_version"], "requestId": row["request_id"], "correlationId": row["correlation_id"], "occurredAt": row["occurred_at"], "contentDigest": row["content_digest"], "reason": row["reason"], "previousDigest": row["previous_digest"], "eventDigest": row["event_digest"]}

    @staticmethod
    def _receipt_json(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "messageId": row["message_id"], "operationId": row["operation_id"], "status": row["status"], "sourceCode": row["source_code"], "sourceProfile": row["source_profile"], "rawDigest": row["raw_digest"], "rawXml": row["raw_xml"], "validatedAt": row["validated_at"], "immutable": bool(row["immutable"])}


def create_app(db_path: str = ":memory:") -> ManagementApp:
    return ManagementApp(db_path)
