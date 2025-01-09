import sys
import time
import threading
from datetime import datetime, timedelta

from loguru import logger

from src.market_scan import market_scan_handler
from src.solve_instances import solve_instances_handler


def run_market_scan():
    """
    Continuously run market scan in a separate thread.
    Fixes #26: Decoupled from solve_instances to allow concurrent operation.
    Market scan runs every 10 seconds to check for new instances.
    """
    while True:
        try:
            logger.info("Starting market scan")
            market_scan_handler()
            logger.info("Market scan completed successfully")
        except Exception as e:
            logger.exception("Error during market scan: " f"{str(e)}")
        time.sleep(10)  # Wait 10 seconds between market scans


def run_solve_instances():
    """
    Continuously run solve instances in a separate thread.
    Fixes #26: Decoupled from market_scan to allow concurrent operation.
    Solve instances runs every 30 seconds to process awarded proposals.
    The longer interval (30s vs 10s) is chosen because solving takes more time.
    """
    while True:
        try:
            logger.info("Starting solve instances")
            solve_instances_handler()
            logger.info("Solve instances completed successfully")
        except Exception as e:
            logger.exception("Error during solve instances: " f"{str(e)}")
        time.sleep(30)  # Wait 30 seconds between solve instances


def main():
    logger.info("Starting application...")
    
    # Create threads for each task
    market_scan_thread = threading.Thread(
        target=run_market_scan,
        name="market_scan_thread",
        daemon=True
    )
    solve_instances_thread = threading.Thread(
        target=run_solve_instances,
        name="solve_instances_thread",
        daemon=True
    )
    
    # Start both threads
    market_scan_thread.start()
    solve_instances_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
            if not market_scan_thread.is_alive() or not solve_instances_thread.is_alive():
                logger.error("One of the worker threads died. Exiting...")
                sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.exception("Fatal error in main loop: " f"{str(e)}")
        sys.exit(1)
