"""Run the local synthetic management API."""

from __future__ import annotations

import argparse
import os
from wsgiref.simple_server import make_server

from .app import MAX_UPLOAD_BYTES, create_app
from .config import RuntimeConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AG Datovka v1 API")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--db", default=None, help="fixture-only SQLite path")
    args = parser.parse_args()
    config = RuntimeConfig.from_env()
    host = args.host or config.host
    port = args.port or config.port
    db_path = args.db or os.environ.get("AG_FIXTURE_DB", os.path.join("data", "ag-datovka.sqlite3"))
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    app = create_app(db_path)
    print(f"AG Datovka API listening on http://{host}:{port}/api/v1 (max upload {config.max_upload_bytes} bytes)")
    try:
        make_server(host, port, app).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


if __name__ == "__main__":
    main()
