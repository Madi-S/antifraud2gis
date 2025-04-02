import dramatiq
import time
import os
# from filelock import FileLock, Timeout
from .fraud import detect
from .company import CompanyList, Company

print("Antifraud2gis worker started")

broker = dramatiq.get_broker()

lock_path = "/tmp/.antifraud.lock"

@dramatiq.actor
def fraud_task(oid: str):
    #lock = FileLock(lock_path)

    #with lock.acquire():

    c = Company(oid)
    cl = CompanyList()
    

    print(f"{os.getpid()} task STARTED {c}")
    detect(c, cl)
    print(f"{os.getpid()} task FINISHED {c}")


