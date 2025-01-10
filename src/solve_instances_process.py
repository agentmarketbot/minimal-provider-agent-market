"""Process that continuously solves awarded instances independently."""

import sys
import time

from loguru import logger

from src.solve_instances import solve_instances_handler


def main() -> None:
    """
    Continuously run solve instances as a standalone process.

    The process runs every 30 seconds to process awarded proposals.
    Handles graceful shutdown on keyboard interrupt.

    Fixes #26: Decoupled from market_scan to allow independent operation.
    """
    logger.info("Starting solve instances process...")

    try:
        while True:
            try:
                logger.info("Starting solve instances")
                solve_instances_handler()
                logger.info("Solve instances completed successfully")
            except Exception as e:
                logger.exception("Error during solve instances: %s", str(e))
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Solve instances process stopped by user")
    except Exception as e:
        logger.exception("Fatal error in solve instances process: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
