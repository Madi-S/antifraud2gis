import dramatiq
import sys
from ..tasks import fraud_task 
from dramatiq.cli import main as dramatiq_main
from ..logger import logger, loginit

"""
af2worker antifraud2gis.tasks
"""
def main():
    sys.argv = ["dramatiq", "-p1", "-t1", "antifraud2gis.tasks"]
    loglevel = "DEBUG" # (or "INFO")
    loginit(loglevel)
    logger.debug(f"Starting dramatiq worker ({loglevel})")
    dramatiq_main()

if __name__ == "__main__":
    main()
