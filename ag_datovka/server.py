"""Run the local synthetic management API."""

from __future__ import annotations

import argparse
import os
from wsgiref.simple_server import make_server

from .app import MAX_UPLOAD_BYTES, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the migration-free AG Datovka v1 API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db", default=os.path.join("data", "ag-datovka.sqlite3"))
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    app = create_app(args.db)
    print(f"AG Datovka API listening on http://{args.host}:{args.port}/api/v1 (max upload {MAX_UPLOAD_BYTES} bytes)")
    try:
        make_server(args.host, args.port, app).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


if __name__ == "__main__":
    main()
