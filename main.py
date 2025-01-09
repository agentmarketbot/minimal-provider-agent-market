import sys
from loguru import logger

def main():
    """
    Main entry point that provides information about how to run the decoupled processes.
    Fixes #26: Market scan and solve instances are now separate processes.
    """
    logger.info("This application has been decoupled into two separate processes:")
    logger.info("1. To run market scan: python3 src/market_scan_process.py")
    logger.info("2. To run solve instances: python3 src/solve_instances_process.py")
    logger.info("Run each process in a separate terminal to operate them independently.")
    logger.info("Use Ctrl+C to gracefully stop each process.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error in main loop: {str(e)}")
        sys.exit(1)
