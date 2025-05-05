import dramatiq
import time
import os
import redis
import json
# from filelock import FileLock, Timeout
from .fraud import detect
from .company import CompanyList, Company
from .exceptions import AFNoCompany, AFReportAlreadyExists, AFCompanyNotFound
from .logger import logger
from .const import REDIS_WORKER_STATUS, REDIS_WORKER_STATUS_SET, REDIS_TRUSTED_LIST, REDIS_UNTRUSTED_LIST, \
    REDIS_TASK_QUEUE_NAME, REDIS_DRAMATIQ_QUEUE
from .user import reset_user_pool
from .statistics import statistics

broker = dramatiq.get_broker()

lock_path = "/tmp/.antifraud.lock"

r = redis.Redis(
    decode_responses=True
)

# r.set(REDIS_WORKER_STATUS, f'worker started as pid {os.getpid()}')

started = time.time()
processed = 0

def get_qsize():
    return r.llen(REDIS_DRAMATIQ_QUEUE)    

def cooldown_queue(maxq: int):
    printed = False
    while get_qsize() >= maxq:
        if not printed:
            logger.debug(f"Queue size {get_qsize()} > {maxq}, waiting to cooldown...")
            printed = True
        time.sleep(10)

def set_status(status: str):
    r.set(REDIS_WORKER_STATUS, status)
    r.set(REDIS_WORKER_STATUS_SET, str(int(time.time())))

@dramatiq.actor
def fraud_task(oid: str, force=False):
    global processed
    #lock = FileLock(lock_path)

    task_started = time.time()

    #with lock.acquire():
    r.lrem(REDIS_TASK_QUEUE_NAME, count=1, value=oid)
    
    try:
        c = Company(oid)
    except (AFNoCompany, AFCompanyNotFound) as e:
        logger.warning(f"Worker: Company {oid!r} not found or broken")
        return
    
    cl = CompanyList()
    
    if c.error:
        logger.warning(f"Worker: Company {oid!r} is error: {c.error} (geo?)")
        return

    print(f"{os.getpid()} task STARTED {c}")
    set_status(oid)
    try:
        score = detect(c, cl, force=force)
    except AFNoCompany:
        logger.warning(f"Worker: Company {oid!r} not found")
        return
    except AFReportAlreadyExists:
        logger.warning(f"Worker: Report for {oid!r} already exists")
        return
    
    
    set_status(f'finished {oid}')
    print(f"{os.getpid()} task FINISHED {c}")
    print("SCORE:", score)

    res = {
        'oid': oid,
        'title': c.title,
        'rating': c.branch_rating_2gis,
        'score': score,
        'address': c.address,
        'trusted': score.get('trusted')
    }

    if score.get('trusted'):
        lname = REDIS_TRUSTED_LIST
    else:
        lname = REDIS_UNTRUSTED_LIST

    r.lpush(lname, json.dumps(res))
    r.ltrim(lname, 0, 19)
    reset_user_pool()
    processed += 1

    logger.info(f"Worker: {oid!r} processed in {int(time.time() - task_started)} sec")
    logger.info(f"Worker total: {processed} tasks in {int(time.time() - started)} sec")
    logger.info(statistics)


def submit_fraud_task(oid: str, force: bool = False):
    fraud_task.send(oid, force=force)
    r.rpush(REDIS_TASK_QUEUE_NAME, oid)

