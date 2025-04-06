import argparse
import time
import random
import pkg_resources

from ..company import CompanyList, Company
from ..user import User
from ..settings import settings
from ..fraud import detect, dump_report
from ..exceptions import AFNoCompany

from .summary import printsummary

from rich.text import Text

def countdown(n=5):
    for i in range(n, 0, -1):
        print(f'\rCountdown: {i}', end=" ", flush=True)
        time.sleep(1)
    print()


def add_dev_parser(subparsers):
    dev_parser = subparsers.add_parser("dev", help="debug utilities for developer")
    dev_parser.add_argument("args", nargs=argparse.REMAINDER)
    dev_parser.add_argument("cmd", choices=['delerror', 'reinit', 'findnew', 'location'])
    dev_parser.add_argument("--real", default=False, action='store_true', help='Run dangerous operation for real (otherwise - dry run)')
    dev_parser.add_argument("--now", default=False, action='store_true', help='No countdown, run immediately')

    return dev_parser


def reinit(cl: CompanyList):
    companies = {
        '70000001094664808': {
            'alias': 'manty',
            'tags': 'x'
        },
        '70000001086696739': {
            'alias': 'vostochnoe',
            'tags': 'x'
        },

        '141266769572238': {
            'alias': 'gcarenda',
            'tags': 'x'
        },

        '70000001020949692': {
            'alias': 'mario',
            'tags': 'x'
        },



        '141265769369926': {
            'alias': 'nskg',
        },



        '70000001023347049': {
            'alias': 'madina',
        },
        '70000001029225378': {
            'alias': 'gorodok',
        },
        '141265770941878': {
            'alias': 'schulz',
        },        


        '141265769369691': {
            'alias': 'rshb',
        },        
        '141265771980582': {
            'alias': 'rshb2',
        },        

        '141265769366331': {
            'alias': 'sber',
        },        

        '141265769882893': {
            'alias': 'raif',
        },       
        
        '70000001063580224': {
            'alias': 'simsim',
        },
        '141265769360673': {
            'alias': 'novat',
        },
        '141265770459396': {
            'alias': 'aura',
        },
        '141265769338187': {
            'alias': 'nskzoo',
        },
        '4504127908731515': {
            'alias': 'mskzoo',
        },
        '985690699467625': {
            'alias': 'roev',
        },
        '70000001080281737': {
            'alias': 'tolmachevo',
        },
        '4504127908780545': {
            'alias': 'domodedovo',
        },
        '4504127921282909': {
            'alias': 'sheremetevo',
        },

        

    }

    companies2 = {
        '70000001029225378': {
            'alias': 'gorodok',
        }
    }

    for path in [ settings.storage, settings.company_storage, settings.user_storage]:
        if not path.exists():
            print(f"Create {path}")
            path.mkdir()

    
    deleted_reports = 0
    for c in cl.companies():
        # c = Company(oid)
        if c.report_path.exists():
            c.report_path.unlink()
            deleted_reports += 1
    print(f"deleted {deleted_reports} old reports")


    for oid, data in companies.items():
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