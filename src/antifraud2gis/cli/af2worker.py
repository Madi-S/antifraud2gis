import dramatiq
import sys
from ..tasks import fraud_task 
from dramatiq.cli import main as dramatiq_main


"""
af2worker antifraud2gis.tasks
"""
def main():
    sys.argv = ["dramatiq", "-p1", "-t1", "antifraud2gis.tasks"]
    dramatiq_main()

if __name__ == "__main__":
    main()
