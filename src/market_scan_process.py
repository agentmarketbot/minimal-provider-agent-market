"""Market scan process that runs independently to check for new instances."""

import sys
import time

from loguru import logger

from src.market_scan import market_scan_handler


def main() -> None:
    """
    Continuously run market scan as a standalone process.

    The process runs every 10 seconds to check for new instances.
    Handles graceful shutdown on keyboard interrupt.

    Fixes #26: Decoupled from solve_instances to allow independent operation.
    """
    logger.info("Starting market scan process...")

    try:
        while True:
            try:
                logger.info("Starting market scan")
                market_scan_handler()
                logger.info("Market scan completed successfully")
            except Exception as e:
                logger.exception("Error during market scan: %s", str(e))
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Market scan process stopped by user")
    except Exception as e:
        logger.exception("Fatal error in market scan process: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
