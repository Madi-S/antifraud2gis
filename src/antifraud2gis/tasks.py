import dramatiq
import time
import os
import redis
import json
# from filelock import FileLock, Timeout
from .fraud import detect
from .company import CompanyList, Company
from .exceptions import AFNoCompany, AFReportAlreadyExists
from .logger import logger
from .const import REDIS_WORKER_STATUS, REDIS_TRUSTED_LIST, REDIS_UNTRUSTED_LIST, REDIS_TASK_QUEUE_NAME

broker = dramatiq.get_broker()

lock_path = "/tmp/.antifraud.lock"

r = redis.Redis(
    decode_responses=True
)

r.set(REDIS_WORKER_STATUS, f'started...')


@dramatiq.actor
def fraud_task(oid: str):
    #lock = FileLock(lock_path)

    #with lock.acquire():
    print(f"remove {oid} from {REDIS_TASK_QUEUE_NAME}")
    x = r.lrem(REDIS_TASK_QUEUE_NAME, count=1, value=oid)
    print(x)

    c = Company(oid)
    cl = CompanyList()
    

    print(f"{os.getpid()} task STARTED {c}")
    r.set(REDIS_WORKER_STATUS, oid)
    try:
        score = detect(c, cl)
    except AFNoCompany:
        logger.warning(f"Worker: Company {oid!r} not found")
        return
    except AFReportAlreadyExists:
        logger.warning(f"Worker: Report for {oid!r} already exists")
        return

    
    
    r.set(REDIS_WORKER_STATUS, f'finished {oid}')
    print(f"{os.getpid()} task FINISHED {c}")
    print("SCORE:", score)

    res = {
        'oid': oid,
        'title': c.title,
        'rating': c.branch_rating_2gis,
        'score': score.get('score'),
        'address': c.address,
        'trusted': score.get('trusted')
    }

    if score.get('trusted'):
        lname = REDIS_TRUSTED_LIST
    else:
        lname = REDIS_UNTRUSTED_LIST

    r.lpush(lname, json.dumps(res))
    r.ltrim(lname, 0, 19)




