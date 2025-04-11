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

from pathlib import Path

from ..company import Company, CompanyList
from ..user import User
from ..fraud import detect, compare, dump_report
from ..logger import loginit, logger, testlogger
from ..db import db
from ..const import SUMMARY_PERIOD
from ..exceptions import AFNoCompany, AFReportNotReady, AFReportAlreadyExists
from ..settings import settings
from ..statistics import statistics

# CLI
from .summary import add_summary_parser, handle_summary, printsummary
from .company import add_company_parser, handle_company
from .user import add_user_parser, handle_user
from .dev import add_dev_parser, handle_dev

last_summary = 0

def UNUSED_get_args():

    aa = ArgAlias()
    aa.alias(["company"], "c")
    aa.alias(["company", "compare"], "cmp")
    aa.alias(["company", "fraud"], "f", "fr")
    aa.alias(["company", "reviews"], "rev")
    aa.alias(["company", "info"], "i")

    aa.alias(["user"], "u", "users")
    aa.alias(["user", "company"], "c", "ci")
    aa.alias(["user", "reviews"], "rev")
    aa.alias(["user", "info"], "i")

    aa.alias(["summary"], "sum", "s")
    aa.alias(["summary", "summary"], "sum")
    aa.alias(["summary", "search"], "se", "s")
    aa.alias(["summary", "table", "TwinScore"], "twin", "ts")
    aa.alias(["summary", "table", "WSS"], "wss")


    aa.skip_flags()
    aa.parse()

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", default=False, action='store_true')
    parser.add_argument("--stop", default=False, action='store_true')

    # add subparser for company
    subparsers = parser.add_subparsers(dest="subparser", help="sub-command help")



    add_summary_parser(subparsers=subparsers)
    add_company_parser(subparsers=subparsers)
    add_user_parser(subparsers=subparsers)
    add_dev_parser(subparsers=subparsers)

    #sum_parser = subparsers.add_parser("summary", help="Operations with whole database")
    #sum_parser.add_argument("cmd", nargs='?', choices=['summary', 'dump', 'table', 'recalc'])
    #sum_parser.add_argument("args", nargs=argparse.REMAINDER)


    return parser.parse_args()
    #return parser.parse_known_args()


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=['list','stop','summary', 'fraud', 'delreport', 'wipe'])
    parser.add_argument("-v", "--verbose", default=False, action='store_true')
    parser.add_argument("--sleep", type=float, default=None, help='sleep N.M seconds after each processed company')
    parser.add_argument("--fmt", "-f", default="normal", choices=['brief', 'normal', 'full'])

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
    #print(args)

    stopfile = Path('.stop')

    cl = CompanyList()

    loginit("DEBUG" if args.verbose else "INFO")


    if args.cmd == "stop":
        stopfile.touch()
        print("Stopfile created in current directory")

    elif args.cmd == "summary":
        if args.fmt == 'full':
            printsummary(cl=cl, full=True)
        else:
            printsummary(cl=cl, full=False)

    elif args.cmd in ["list", "fraud", "delreport", "wipe"]:

        # if company is given, create it first (if it's missing)
        if args.company and args.cmd not in ['wipe']:
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

        for c in cl.companies(oid=args.company, name=args.name, town=args.town, report=args.report, noreport=args.noreport):

            total_processed += 1

            if args.cmd == "list":
                if args.fmt == "brief":
                    _print(c.object_id)
                else:
                    print(c)

            elif args.cmd == "fraud":
                print("FF", c)

                if args.show:
                    settings.show_hit_th = args.show
                try:
                    detect(c, cl, force=args.overwrite)
                    effectively_processed += 1
                    dump_report(c.object_id)
                except AFReportAlreadyExists as e:
                    print(f"Report already exists for {c}")

            elif args.cmd == "delreport":                
                print(f"Delete report for {c}")
                c.report_path.unlink(missing_ok=True)

            elif args.cmd == "wipe":
                if args.really:
                    print(f"wipe {c}")
                    c.wipe(c.object_id)
                else:
                    print("[NOT REALLY] wipe", c)

            
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


        if args.fmt == 'normal':
            # POST PROCESSING
            if args.cmd == "fraud":
                print(f'# Fraud reports calculated {effectively_processed}')

            print(f'# Total processed {total_processed} comanies')
            print(statistics)
