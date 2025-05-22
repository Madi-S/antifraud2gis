from loguru import logger
import sys
from pathlib import Path



def loginit(level: str = "INFO"):
    logger.remove()
    
    logger.add(Path("~/2gis.log").expanduser(), level="DEBUG", rotation="100 MB", compression="zip", format="{time:YYYY-MM-DD HH:mm:ss} {message}")
    logger.add(sys.stderr, level=level, format="{time:YYYY-MM-DD HH:mm:ss} {message}")

def testlogger():
    logger.debug("Debug test message")
    logger.info("Info test message")
    logger.success("Success test message")
    logger.warning("Warning test message")
    logger.error("Error test message")
    logger.critical("Critical test message")
