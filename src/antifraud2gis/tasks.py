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
from .const import REDIS_WORKER_STATUS, REDIS_TRUSTED_LIST, REDIS_UNTRUSTED_LIST, REDIS_TASK_QUEUE_NAME, REDIS_DRAMATIQ_QUEUE
from .user import reset_user_pool
from .statistics import statistics
from .search import index_company

broker = dramatiq.get_broker()

lock_path = "/tmp/.antifraud.lock"

r = redis.Redis(
    decode_responses=True
)

r.set(REDIS_WORKER_STATUS, f'started...')

started = time.time()
processed = 0

def get_qsize():
    return r.llen(REDIS_DRAMATIQ_QUEUE)    

def cooldown_queue(maxq: int):
    while get_qsize() > maxq:
        time.sleep(10)

@dramatiq.actor
def fraud_task(oid: str, force=False):
    global processed
    #lock = FileLock(lock_path)

    task_started = time.time()

    #with lock.acquire():
    r.lrem(REDIS_TASK_QUEUE_NAME, count=1, value=oid)
    
    try:
        c = Company(oid)
    except AFNoCompany as e:
        logger.warning(f"Worker: Company {oid!r} not found")
        return
    
    cl = CompanyList()
    
    if c.error:
        logger.warning(f"Worker: Company {oid!r} is error: {c.error} (geo?)")
        return

    print(f"{os.getpid()} task STARTED {c}")
    r.set(REDIS_WORKER_STATUS, oid)
    try:
        score = detect(c, cl, force=force)
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
    reset_user_pool()
    processed += 1

    logger.info(f"Worker: {oid!r} processed in {int(time.time() - task_started)} sec")
    logger.info(f"Worker total: {processed} tasks in {int(time.time() - started)} sec")
    logger.info(statistics)


def submit_fraud_task(oid: str, force: bool = False):
    fraud_task.send(oid, force=force)
    r.rpush(REDIS_TASK_QUEUE_NAME, oid)

