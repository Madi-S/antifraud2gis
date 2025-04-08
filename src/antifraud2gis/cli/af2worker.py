import dramatiq
from ..tasks import fraud_task 
from dramatiq.cli import main as dramatiq_main


"""
af2worker antifraud2gis.tasks
"""
def main():
    dramatiq_main()

if __name__ == "__main__":
    main()
