import argparse
import time
import random
import pkg_resources
import redis
from rich.text import Text

from ..company import CompanyList, Company
from ..user import User
from ..settings import settings
from ..fraud import detect, dump_report
from ..exceptions import AFNoCompany
from ..aliases import aliases
from .summary import printsummary
from ..const import REDIS_TASK_QUEUE_NAME, REDIS_TRUSTED_LIST, REDIS_UNTRUSTED_LIST, REDIS_WORKER_STATUS, REDIS_DRAMATIQ_QUEUE

def countdown(n=5):
    for i in range(n, 0, -1):
        print(f'\rCountdown: {i}', end=" ", flush=True)
        time.sleep(1)
    print()


def add_dev_parser(subparsers):
    dev_parser = subparsers.add_parser("dev", help="debug utilities for developer")
    # dev_parser.add_argument("args", nargs=argparse.REMAINDER)
    dev_parser.add_argument("cmd", choices=['delerror', 'reinit', 'findnew', 'location', 'tmp'])
    dev_parser.add_argument("--real", default=False, action='store_true', help='Run dangerous operation for real (otherwise - dry run)')
    dev_parser.add_argument("--now", default=False, action='store_true', help='No countdown, run immediately')
    dev_parser.add_argument("args", nargs='*', help='extra args')

    return dev_parser


def reinit(cl: CompanyList):

    for path in [ settings.storage, settings.company_storage, settings.user_storage]:
        if not path.exists():
            print(f"Create {path}")
            path.mkdir()

    
    deleted_reports = 0
    for c in cl.companies():
        if c.report_path.exists():
            c.report_path.unlink()
            deleted_reports += 1
    print(f"deleted {deleted_reports} old reports")


    for oid, data in aliases.items():
        c = Company(oid)
        c.load_basic_from_network()
        if 'alias' in data:
            c.alias = data['alias']
            print(c)
        if 'tags' in data:
            c.tags = data['tags']
        c.save_basic()


def findnew():

    found = False

    # read random user
    cl = CompanyList()
    files = [f for f in settings.user_storage.iterdir() if f.is_file()]

    while not found:
        uid = random.choice(files).name.split('-')[0]
        u = User(uid)
        for r in u.reviews():
            print(r)
            try:
                c = cl[r.oid]
                print("Exist:", c)
            except KeyError as e:
                try:
                    c = Company(r.oid)
                except AFNoCompany as e:
                    continue
                detect(c, cl)
                dump_report(r.oid)
                found = True
    
    printsummary(cl)



def handle_dev(args: argparse.Namespace):
    cmd = args.cmd
    cl = CompanyList()

    total = 0
    errors = 0

    if cmd == "delerror":
        if args.real:
            print("Running in REAL mode")
            if not args.now:
                countdown()
        else:
            print("Running in dry run mode")

        for c in cl.companies():
            total += 1
            if c.error is not None:
                print("deleting", c)
                c.delete()
                errors += 1
        print(f"Total/Err: {total} / {errors} ")

    elif cmd == "reinit":
        if args.real:
            print("Running in REAL mode")
            if not args.now:
                countdown()
            reinit(cl)
        else:
            print("Running in dry run mode")

    elif cmd == "location":
        print(pkg_resources.resource_filename("antifraud2gis", ""))
    elif cmd == "findnew":
        findnew()
    elif cmd == "tmp":
        # check users age for review
        u = User(args.args[0])
        print(u.birthday())


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=['company-users', 'user-reviews', 'queue'])
    parser.add_argument("-v", "--verbose", default=False, action='store_true')
    parser.add_argument("--full", default=False, action='store_true')
    parser.add_argument("args", nargs='*', help='extra args')

    g = parser.add_argument_group('Company selection')
    g.add_argument("-t", "--town", default=None, help="Filter by town")
    g.add_argument("-n", "--name", default=None, help="Filter by name (fnmatch)")
    g.add_argument("-l", "--limit", metavar='N', type=int, help="Limit to N companies")
    g.add_argument("-c", "--company", metavar='OID', help="Company ID")
    g.add_argument("--report", default=None, action='store_true', help="Company has antifraud report")
    g.add_argument("--noreport", default=None, action='store_true', help="Company has NO antifraud report")
    g.add_argument("--really", default=None, action='store_true', help="Really. (flag for dangerous commands like wipe)")
    
    g = parser.add_argument_group('Fraud options')
    g.add_argument("-s", "--show", metavar='N', type=int, help="Show links with N hits")
    g.add_argument("--overwrite", default=None, action='store_true', help="Recalculate even if fraud report exists")

    return parser.parse_args()

def main():
    args = get_args()
    cl = CompanyList()

    cmd = args.cmd

    if cmd == "company-users":
        c = cl[args.company]
        print(c)
        c.load_reviews()
        for u in c.users():
            print(u)

    if cmd == "user-reviews":

        u = User(args.args[0])
        for r in u.reviews():
            print(r)

    elif cmd == "queue":
        r = redis.Redis(decode_responses=True)

        if 'reset' in args.args:
            print("RESET queue")
            r.delete(REDIS_TASK_QUEUE_NAME)
            r.delete(REDIS_TRUSTED_LIST)
            r.delete(REDIS_UNTRUSTED_LIST)

        wstatus = r.get(REDIS_WORKER_STATUS)
        tasks = r.lrange(REDIS_TASK_QUEUE_NAME, 0, -1)  # возвращает list of bytes    
        trusted_len = r.llen(REDIS_TRUSTED_LIST)
        untrusted_len = r.llen(REDIS_UNTRUSTED_LIST)
        dqlen = r.llen(REDIS_DRAMATIQ_QUEUE)

        print("Queue report")
        print(f"Worker status: {wstatus}")
        print(f"Dramatiq queue: {dqlen}")
        print(f"Tasks ({len(tasks)}): {tasks[:5]} ")
        print(f"Trusted ({trusted_len})")
        print(f"Untrusted ({untrusted_len})")
