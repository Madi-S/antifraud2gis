#!/usr/bin/env python3

import argparse
import sys
import time
import json
from builtins import print as _print

from argalias import ArgAlias

from rich import print_json, print
from rich.console import Console
from rich.table import Table
import redis
import gzip

from pathlib import Path

from ..company import Company, CompanyList
from ..user import User
from ..fraud import detect, dump_report
from ..compare import compare
from ..tasks import submit_fraud_task, cooldown_queue
from ..logger import loginit, logger, testlogger
from ..db import db
from ..const import REDIS_DRAMATIQ_QUEUE
from ..exceptions import AFNoCompany, AFReportNotReady, AFReportAlreadyExists
from ..settings import settings
from ..statistics import statistics
from ..aliases import resolve_alias
from ..search import search

# CLI
from .summary import printsummary

# from .summary import add_summary_parser, handle_summary, printsummary
#from .company import add_company_parser, handle_company
#from .user import add_user_parser, handle_user
#from .dev import add_dev_parser, handle_dev

last_summary = 0

def get_args():


    aa = ArgAlias()
    aa.alias(["list"], "l")
    aa.alias(["info"], "i")
    aa.alias(["fraud"], "f", "fr")
    aa.alias(["submitfraud"], "sf", "sfr")
    
    aa.skip_flags()
    aa.parse()

    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=['info', 'list','stop','summary', 'fraud', 'compare', 'submitfraud', 'delreport', 'wipe', 'export', 'search'])
    parser.add_argument("-v", "--verbose", default=False, action='store_true')
    parser.add_argument("--sleep", type=float, default=None, help='sleep N.M seconds after each processed company')
    parser.add_argument("--fmt", "-f", default="normal", choices=['brief', 'normal', 'full'])
    parser.add_argument("args", nargs='*')

    g = parser.add_argument_group('Company selection')
    g.add_argument("-t", "--town", default=None, help="Filter by town")
    g.add_argument("-n", "--name", default=None, help="Filter by name (fnmatch)")
    g.add_argument("-l", "--limit", metavar='N', type=int, help="Limit to N companies")
    g.add_argument("-d", "--detection", metavar='DETECTION', help="Only with this detection. also trusted, untrusted")
    g.add_argument("-c", "--company", metavar='OID', help="Company ID")
    g.add_argument("--report", default=None, action='store_true', help="Company has antifraud report")
    g.add_argument("--noreport", default=None, action='store_true', help="Company has NO antifraud report")
    g.add_argument("--really", default=None, action='store_true', help="Really. (flag for dangerous commands like wipe)")
    
    g = parser.add_argument_group('Fraud options')
    g.add_argument("-s", "--show", metavar='N', type=int, help="Show links with N hits")
    g.add_argument("--overwrite", default=None, action='store_true', help="Recalculate even if fraud report exists")
    g.add_argument("--explain", default=False, action='store_true', help="Re-run fraud detection with explanation")
    g.add_argument("--maxq", metavar='N', default=None, type=int, help="Sleep if redis queue is over N")

    return parser.parse_args()

def any_filter(args):
    return args.company or args.name or args.town or args.detection or args.report or args.noreport

def main():
    args = get_args()

    stopfile = Path('~/.af2gis-stop').expanduser()
    
    r = redis.Redis(decode_responses=True)

    cl = CompanyList()

    loginit("DEBUG" if args.verbose else "INFO")


    if args.cmd == "stop":
        stopfile.touch()
        print(f"Stopfile {stopfile} created")

    elif args.cmd == "summary":
        if args.fmt == 'full':
            printsummary(cl=cl, full=True)
        else:
            printsummary(cl=cl, full=False)

    elif args.cmd == "compare":
        if len(args.args) != 2:
            print("Need 2 companies")
            sys.exit(1)
        c1 = cl[args.args[0]]
        c2 = cl[args.args[1]]
        compare(c1, c2)

    elif args.cmd == "info":
        c = Company(args.company)
        basic = json.load(gzip.open(c.basic_path))
        print(c)
        print_json(data=basic)

        try:
            report = json.load(gzip.open(c.report_path))
        except FileNotFoundError:
            print("No report yet, run fraud first")
            return
        print_json(data=report['score'])
        print(f"{len(report['relations'])} relations")
        
    elif args.cmd == "search":
        res = search(args.args[0])
        for rec in res:
            print(rec)
        

    elif args.cmd in ["list", "fraud", "delreport", "wipe", "submitfraud", "export"]:

        # sanity check
        if args.cmd in ["submitfraud", "delreport", "wipe"] and not any_filter(args):
            print(f"Need company filter for {args.cmd}")
            sys.exit(1)

        # if company is given, create it first (if it's missing)
        if args.company and args.cmd not in ['wipe', 'submitfraud']:
            Company(args.company)
        
        # PRE PROCESSING
        if args.cmd == "delreport":
            # force args.report
            args.report = True
        elif args.cmd == "fraud":
            if args.show:
                settings.show_hit_th = args.show

        total_processed = 0
        effectively_processed = 0


        for c in cl.companies(oid=args.company, name=args.name, town=args.town, detection=args.detection, report=args.report, noreport=args.noreport):

            total_processed += 1

            if args.cmd == "list":
                if args.fmt == "brief":
                    _print(c.object_id)
                else:
                    print(c)

            elif args.cmd == "fraud":

                if args.show:
                    settings.show_hit_th = args.show
                try:
                    detect(c, cl, explain=args.explain, force=args.overwrite)
                    effectively_processed += 1
                except AFReportAlreadyExists as e:
                    print(f"Report already exists for {c} and no --overwrite")
                dump_report(c.object_id)

            elif args.cmd == "submitfraud":
                if args.maxq:
                    cooldown_queue(args.maxq)
                print("submit fraud request for", c)
                submit_fraud_task(oid = c.object_id, force=args.overwrite)


            elif args.cmd == "delreport":                
                print(f"Delete report for {c}")
                c.report_path.unlink(missing_ok=True)
                c.explain_path.unlink(missing_ok=True)
                c.trusted = None
                c.detections = list()
                c.save_basic()


            elif args.cmd == "wipe":
                if args.really:
                    print(f"wipe {c}")
                    c.wipe(c.object_id)
                else:
                    print("[NOT REALLY] wipe", c)

            elif args.cmd == "export":
                _print(json.dumps(c.export()))
            
            # Stop if stopfile
            if stopfile.exists():
                print("Stopfile found, exit")
                stopfile.unlink()
                sys.exit(0)
        
            # Stop if processed enough
            if args.limit:
                if args.cmd == "fraud":
                    if effectively_processed >= args.limit:
                        print(f"Processed {args.limit} companies, exit")
                        break
                else:
                    if total_processed >= args.limit:
                        print(f"Processed {args.limit} companies, exit")
                        break
            
            if args.sleep:
                time.sleep(args.sleep)


        if args.fmt == 'normal' and args.cmd not in ['export']:
            # POST PROCESSING
            if args.cmd == "fraud":
                print(f'# Fraud reports calculated {effectively_processed}')

            print(f'# Total processed {total_processed} comanies')
            print(statistics)
