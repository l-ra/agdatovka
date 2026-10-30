"""Durable, dependency-free content and message delivery primitives.

The module is deliberately adapter-neutral.  Bytes enter through an iterator,
are written incrementally to a local object-store boundary, and are represented
in the queue by a checksummed manifest.  Delivery is an outbox transaction
followed by leased work; an adapter is supplied by the caller and is never
invoked by the management API itself.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO, Callable, Iterable, Iterator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ContentManifest:
    content_id: str
    media_type: str
    filename: str
    byte_length: int
    sha256: str
    object_path: str

    @property
    def digest(self) -> str:
        return f"sha256:{self.sha256}"

    def as_dict(self) -> dict[str, object]:
        return {
            "contentId": self.content_id,
            "filename": self.filename,
            "mediaType": self.media_type,
            "byteLength": self.byte_length,
            "contentDigest": self.digest,
            "objectPath": self.object_path,
        }


class ContentStore:
    """A streaming object-store seam.  The file is atomically published."""

    def __init__(self, root: str | os.PathLike[str], max_bytes: int = 512 * 1024 * 1024) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes

    def put(self, chunks: Iterable[bytes], *, filename: str, media_type: str = "application/octet-stream", expected_digest: str | None = None) -> ContentManifest:
        content_id = "content_" + secrets.token_hex(16)
        temporary = self.root / f".{content_id}.part"
        target = self.root / content_id
        hasher = hashlib.sha256()
        length = 0
        try:
            with temporary.open("wb") as stream:
                for chunk in chunks:
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise TypeError("content chunks must be bytes")
                    raw = bytes(chunk)
                    length += len(raw)
                    if length > self.max_bytes:
                        raise ValueError("content exceeds the configured limit")
                    hasher.update(raw)
                    stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            actual = hasher.hexdigest()
            expected = expected_digest.removeprefix("sha256:") if expected_digest else None
            if expected and actual != expected:
                raise ValueError("content checksum does not match manifest")
            os.replace(temporary, target)
            return ContentManifest(content_id, media_type, filename, length, actual, str(target))
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def open(self, manifest: ContentManifest) -> BinaryIO:
        return open(manifest.object_path, "rb")


@dataclass(frozen=True)
class QueueItem:
    operation_id: str
    message_id: str
    attempt: int
    lease_token: str


class DurablePipeline:
    """Transactional outbox, bounded queue, leases, retries and dead letters."""

    RETRYABLE = {"timeout", "429", "500", "502", "503", "504", "upstream_timeout"}

    def __init__(self, connection: sqlite3.Connection, *, max_in_flight: int = 1000, max_attempts: int = 5, base_backoff_seconds: int = 1) -> None:
        self.db = connection
        self.db.row_factory = sqlite3.Row
        self.max_in_flight = max_in_flight
        self.max_attempts = max_attempts
        self.base_backoff_seconds = base_backoff_seconds
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS pipeline_outbox (
              operation_id TEXT PRIMARY KEY, message_id TEXT NOT NULL,
              payload_json TEXT NOT NULL, created_at TEXT NOT NULL, published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS pipeline_queue (
              operation_id TEXT PRIMARY KEY, message_id TEXT NOT NULL,
              payload_json TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL,
              available_at TEXT NOT NULL, lease_token TEXT, leased_until TEXT,
              last_error TEXT, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pipeline_dead_letters (
              operation_id TEXT PRIMARY KEY, message_id TEXT NOT NULL,
              payload_json TEXT NOT NULL, attempts INTEGER NOT NULL,
              reason TEXT NOT NULL, failed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pipeline_metrics (
              name TEXT PRIMARY KEY, value INTEGER NOT NULL
            );
            """
        )
        self.db.commit()

    def _metric(self, name: str, amount: int = 1) -> None:
        self.db.execute("INSERT INTO pipeline_metrics(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=value+excluded.value", (name, amount))

    def enqueue(self, operation_id: str, message_id: str, payload_json: str, *, now: datetime | None = None) -> bool:
        """Insert the outbox record exactly once; a dispatcher publishes it later."""
        at = iso(now or utc_now())
        before = self.db.total_changes
        self.db.execute("INSERT OR IGNORE INTO pipeline_outbox(operation_id,message_id,payload_json,created_at,published_at) VALUES(?,?,?,?,NULL)", (operation_id, message_id, payload_json, at))
        inserted = self.db.total_changes != before
        self._metric("outbox_enqueued" if inserted else "outbox_duplicate")
        self.db.commit()
        return inserted

    def dispatch(self, *, limit: int = 100, now: datetime | None = None) -> int:
        """Move committed outbox rows to the durable queue, idempotently."""
        at = iso(now or utc_now())
        rows = self.db.execute("SELECT * FROM pipeline_outbox WHERE published_at IS NULL ORDER BY created_at,operation_id LIMIT ?", (limit,)).fetchall()
        for row in rows:
            self.db.execute("INSERT OR IGNORE INTO pipeline_queue(operation_id,message_id,payload_json,status,attempts,available_at,lease_token,leased_until,last_error,updated_at) VALUES(?,?,?,'ready',0,?,NULL,NULL,NULL,?)", (row["operation_id"], row["message_id"], row["payload_json"], at, at))
            self.db.execute("UPDATE pipeline_outbox SET published_at=? WHERE operation_id=? AND published_at IS NULL", (at, row["operation_id"]))
        if rows:
            self._metric("outbox_dispatched", len(rows))
        self.db.commit()
        return len(rows)

    def claim(self, worker_id: str, *, now: datetime | None = None, lease_seconds: int = 60) -> QueueItem | None:
        current = now or utc_now()
        active = self.db.execute("SELECT COUNT(*) FROM pipeline_queue WHERE status='leased' AND leased_until>?", (iso(current),)).fetchone()[0]
        if active >= self.max_in_flight:
            self._metric("backpressure_rejected")
            self.db.commit()
            return None
        row = self.db.execute("SELECT * FROM pipeline_queue WHERE (status='ready' OR (status='leased' AND leased_until<?)) AND available_at<=? ORDER BY available_at,operation_id LIMIT 1", (iso(current), iso(current))).fetchone()
        if not row:
            return None
        token = f"{worker_id}:{secrets.token_hex(8)}"
        updated = self.db.execute("UPDATE pipeline_queue SET status='leased',lease_token=?,leased_until=?,updated_at=? WHERE operation_id=? AND (status='ready' OR leased_until<?)", (token, iso(current + timedelta(seconds=lease_seconds)), iso(current), row["operation_id"], iso(current))).rowcount
        if not updated:
            return None
        self._metric("queue_claimed")
        self.db.commit()
        return QueueItem(row["operation_id"], row["message_id"], row["attempts"], token)

    def complete(self, item: QueueItem, *, now: datetime | None = None) -> bool:
        at = iso(now or utc_now())
        changed = self.db.execute("UPDATE pipeline_queue SET status='completed',updated_at=?,leased_until=NULL WHERE operation_id=? AND lease_token=?", (at, item.operation_id, item.lease_token)).rowcount
        if changed:
            self._metric("queue_completed")
            self.db.commit()
        return bool(changed)

    def fail(self, item: QueueItem, reason: str, *, now: datetime | None = None) -> str:
        current = now or utc_now()
        row = self.db.execute("SELECT * FROM pipeline_queue WHERE operation_id=? AND lease_token=?", (item.operation_id, item.lease_token)).fetchone()
        if not row:
            return "lost_lease"
        attempt = row["attempts"] + 1
        retryable = reason in self.RETRYABLE or reason.startswith("5")
        if retryable and attempt < self.max_attempts:
            delay = self.base_backoff_seconds * (2 ** (attempt - 1))
            self.db.execute("UPDATE pipeline_queue SET status='ready',attempts=?,available_at=?,lease_token=NULL,leased_until=NULL,last_error=?,updated_at=? WHERE operation_id=?", (attempt, iso(current + timedelta(seconds=delay)), reason, iso(current), item.operation_id))
            result = "retry_wait"
            self._metric("queue_retried")
        else:
            self.db.execute("UPDATE pipeline_queue SET status='dead_letter',attempts=?,last_error=?,lease_token=NULL,leased_until=NULL,updated_at=? WHERE operation_id=?", (attempt, reason, iso(current), item.operation_id))
            self.db.execute("INSERT OR REPLACE INTO pipeline_dead_letters(operation_id,message_id,payload_json,attempts,reason,failed_at) VALUES(?,?,?,?,?,?)", (row["operation_id"], row["message_id"], row["payload_json"], attempt, reason, iso(current)))
            result = "dead_letter"
            self._metric("queue_dead_lettered")
        self.db.commit()
        return result

    def process_once(self, worker_id: str, handler: Callable[[QueueItem], None], *, now: datetime | None = None) -> str:
        item = self.claim(worker_id, now=now)
        if not item:
            return "empty"
        try:
            handler(item)
        except Exception as error:
            return self.fail(item, str(error) or "upstream_timeout", now=now)
        self.complete(item, now=now)
        return "completed"

    def status(self, operation_id: str) -> dict[str, object] | None:
        row = self.db.execute("SELECT * FROM pipeline_queue WHERE operation_id=?", (operation_id,)).fetchone()
        if row:
            return {"operationId": row["operation_id"], "messageId": row["message_id"], "status": row["status"], "attempts": row["attempts"], "lastError": row["last_error"]}
        row = self.db.execute("SELECT * FROM pipeline_outbox WHERE operation_id=?", (operation_id,)).fetchone()
        return {"operationId": row["operation_id"], "messageId": row["message_id"], "status": "outbox_pending", "attempts": 0, "lastError": None} if row else None

    def metrics(self) -> dict[str, int]:
        return {row["name"]: row["value"] for row in self.db.execute("SELECT name,value FROM pipeline_metrics")}
