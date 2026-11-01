import hashlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ag_datovka.pipeline import ContentStore, DurablePipeline


class StreamingPipelineTest(unittest.TestCase):
    def test_streaming_manifest_checksums_without_joining_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContentStore(directory, max_bytes=32)
            chunks = (part for part in (b"hello ", b"world", b"!"))
            expected = hashlib.sha256(b"hello world!").hexdigest()
            manifest = store.put(chunks, filename="fixture.txt", media_type="text/plain", expected_digest=expected)
            self.assertEqual(manifest.byte_length, 12)
            self.assertEqual(manifest.digest, f"sha256:{expected}")
            with store.open(manifest) as content:
                self.assertEqual(content.read(), b"hello world!")
            with self.assertRaises(ValueError):
                store.put((b"wrong",), filename="bad", expected_digest="sha256:" + "0" * 64)

    def test_interrupted_upload_is_not_published_and_resume_has_one_object(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContentStore(directory, max_bytes=64)

            def interrupted():
                yield b"prefix-"
                raise OSError("synthetic connection interruption")

            with self.assertRaises(OSError):
                store.put(interrupted(), filename="resume.bin")
            self.assertEqual(list(store.root.iterdir()), [])
            manifest = store.put((part for part in (b"prefix-", b"suffix")), filename="resume.bin")
            self.assertEqual([path.name for path in store.root.iterdir()], [manifest.content_id])
            self.assertEqual(manifest.byte_length, len(b"prefix-suffix"))
            with store.open(manifest) as stream:
                self.assertEqual(stream.read(), b"prefix-suffix")

    def test_outbox_dispatch_and_duplicate_submission_are_idempotent(self):
        connection = sqlite3.connect(":memory:")
        pipeline = DurablePipeline(connection)
        self.assertTrue(pipeline.enqueue("op-1", "msg-1", '{"messageId":"msg-1"}'))
        self.assertFalse(pipeline.enqueue("op-1", "msg-1", '{"messageId":"msg-1"}'))
        self.assertEqual(pipeline.dispatch(), 1)
        self.assertEqual(pipeline.dispatch(), 0)
        self.assertEqual(pipeline.status("op-1")["status"], "ready")

    def test_retry_backoff_dead_letter_and_restart_recovery(self):
        connection = sqlite3.connect(":memory:")
        pipeline = DurablePipeline(connection, max_attempts=3, base_backoff_seconds=2)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        pipeline.enqueue("op-2", "msg-2", "{}")
        pipeline.dispatch(now=now)
        self.assertEqual(pipeline.process_once("worker-a", lambda _: (_ for _ in ()).throw(RuntimeError("429")), now=now), "retry_wait")
        self.assertEqual(pipeline.status("op-2")["status"], "ready")
        later = now + timedelta(seconds=2)
        self.assertEqual(pipeline.process_once("worker-a", lambda _: (_ for _ in ()).throw(RuntimeError("upstream_timeout")), now=later), "retry_wait")
        later += timedelta(seconds=4)
        self.assertEqual(pipeline.process_once("worker-a", lambda _: (_ for _ in ()).throw(RuntimeError("503")), now=later), "dead_letter")
        self.assertEqual(pipeline.status("op-2")["status"], "dead_letter")

    def test_backpressure_and_lease_expiry_allow_recovery(self):
        connection = sqlite3.connect(":memory:")
        pipeline = DurablePipeline(connection, max_in_flight=1)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        pipeline.enqueue("op-3", "msg-3", "{}")
        pipeline.enqueue("op-4", "msg-4", "{}")
        pipeline.dispatch(now=now)
        first = pipeline.claim("crashed-worker", now=now, lease_seconds=1)
        self.assertIsNotNone(first)
        self.assertIsNone(pipeline.claim("other-worker", now=now))
        recovered = pipeline.claim("other-worker", now=now + timedelta(seconds=2), lease_seconds=30)
        self.assertIsNotNone(recovered)
        self.assertEqual(pipeline.metrics()["backpressure_rejected"], 1)


if __name__ == "__main__":
    unittest.main()
