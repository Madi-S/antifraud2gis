import dramatiq
import time
import os
import redis
import json
# from filelock import FileLock, Timeout
from .fraud import detect
from .company import CompanyList, Company


print("Antifraud2gis worker started")

broker = dramatiq.get_broker()

lock_path = "/tmp/.antifraud.lock"

r = redis.Redis(
    decode_responses=True
)

@dramatiq.actor
def fraud_task(oid: str):
    #lock = FileLock(lock_path)

    #with lock.acquire():

    c = Company(oid)
    cl = CompanyList()
    

    print(f"{os.getpid()} task STARTED {c}")
    r.set('af2gis:worker_status', f'processing {oid}')
    score = detect(c, cl)
    r.set('af2gis:worker_status', f'finished {oid}')
    print(f"{os.getpid()} task FINISHED {c}")
    print("SCORE:", score)

    res = {
        'oid': oid,
        'title': c.title,
        'address': c.address,
        'trusted': score.get('trusted')
    }

    if score.get('trusted'):
        lname = 'af2gis:last_trusted'
    else:
        lname = 'af2gis:last_untrusted'

    r.lpush(lname, json.dumps(res))
    r.ltrim(lname, 0, 19)




