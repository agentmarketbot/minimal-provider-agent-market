"""Process that continuously solves awarded instances independently."""

import sys
import time

from loguru import logger

from src.config import Settings
from src.solve_instances import solve_instances_handler
from src.utils.git import accept_repo_invitations


def main() -> None:
    """
    Continuously run solve instances as a standalone process.

    The process runs every 30 seconds to process awarded proposals.
    Handles graceful shutdown on keyboard interrupt.

    Fixes #26: Decoupled from market_scan to allow independent operation.
    """
    logger.info("Starting solve instances process...")

    try:
        counter = 0
        while True:
            try:
                logger.info("Starting solve instances")
                solve_instances_handler()
                logger.info("Solve instances completed successfully")
                if counter == 1:
                    logger.info("Accepting invitations to private repos")
                    accept_repo_invitations(Settings.github_pat)
                    logger.info("Finished accepting invitations to private repos")
            except Exception as e:
                logger.exception("Error during solve instances: %s", str(e))
            time.sleep(30)
            counter = (counter + 1) % 10
    except KeyboardInterrupt:
        logger.info("Solve instances process stopped by user")
    except Exception as e:
        logger.exception("Fatal error in solve instances process: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
