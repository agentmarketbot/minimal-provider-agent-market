import time
from loguru import logger

from solve_instances import solve_instances_handler

def main():
    """
    Continuously run solve instances as a standalone process.
    Fixes #26: Decoupled from market_scan to allow independent operation.
    Solve instances runs every 30 seconds to process awarded proposals.
    """
    logger.info("Starting solve instances process...")
    
    try:
        while True:
            try:
                logger.info("Starting solve instances")
                solve_instances_handler()
                logger.info("Solve instances completed successfully")
            except Exception as e:
                logger.exception(f"Error during solve instances: {str(e)}")
            time.sleep(30)  # Wait 30 seconds between solve instances
    except KeyboardInterrupt:
        logger.info("Solve instances process stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error in solve instances process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    main()