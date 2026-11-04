"""Container entry point for the durable worker role.

The queue adapter is deliberately injected by the deployment.  The local
fixture worker is still explicit and in-process; this process only provides a
stable role boundary and refuses fixture configuration in deploy profiles.
"""

from __future__ import annotations

import argparse
import logging
import time

from .config import RuntimeConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="AG Datovka durable worker role")
    parser.add_argument("--once", action="store_true", help="validate configuration and exit")
    args = parser.parse_args()
    config = RuntimeConfig.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("worker role ready queue=%s auth_profile=%s", config.queue_url, config.auth_profile)
    if args.once:
        return
    while True:
        # Provider-specific queue consumption is an adapter boundary.  A real
        # deployment replaces this loop with the approved queue consumer.
        time.sleep(5)


if __name__ == "__main__":
    main()

