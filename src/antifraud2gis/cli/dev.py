import argparse
import time
from ..company import CompanyList, Company
from ..user import User

def countdown(n=5):
    for i in range(n, 0, -1):
        print(f'\rCountdown: {i}', end=" ", flush=True)
        time.sleep(1)
    print()


def add_dev_parser(subparsers):
    util_parser = subparsers.add_parser("dev", help="debug utilities for developer")
    util_parser.add_argument("cmd", choices=['delerror', 'reinit'])
    util_parser.add_argument("--real", default=False, action='store_true', help='Run dangerous operation for real (otherwise - dry run)')
    util_parser.add_argument("--now", default=False, action='store_true', help='No countdown, run immediately')

    return util_parser


def reinit(cl: CompanyList):
    companies = {
        '70000001094664808': {
            'alias': 'manty',
            'tags': 'x'
        },
        '70000001023347049': {
            'alias': 'madina',
        },
        '70000001029225378': {
            'alias': 'gorodok',
        },
        '70000001063580224': {
            'alias': 'simsim',
        },
        '141265769360673': {
            'alias': 'novat',
        },
    }

    companies2 = {
        '70000001029225378': {
            'alias': 'gorodok',
        }
    }


    for oid, data in companies.items():
        c = Company(oid)
        c.load_basic_from_network()
        if 'alias' in data:
            c.alias = data['alias']
            print(c)
        if 'tags' in data:
            c.tags = data['tags']
        c.save_basic()



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

    if cmd =="reinit":
        if args.real:
            print("Running in REAL mode")
            if not args.now:
                countdown()
            reinit(cl)
        else:
            print("Running in dry run mode")

