import time
from loguru import logger

from market_scan import market_scan_handler

def main():
    """
    Continuously run market scan as a standalone process.
    Fixes #26: Decoupled from solve_instances to allow independent operation.
    Market scan runs every 10 seconds to check for new instances.
    """
    logger.info("Starting market scan process...")
    
    try:
        while True:
            try:
                logger.info("Starting market scan")
                market_scan_handler()
                logger.info("Market scan completed successfully")
            except Exception as e:
                logger.exception(f"Error during market scan: {str(e)}")
            time.sleep(10)  # Wait 10 seconds between market scans
    except KeyboardInterrupt:
        logger.info("Market scan process stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error in market scan process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    main()