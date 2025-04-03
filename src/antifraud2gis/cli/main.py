#!/usr/bin/env python3

import argparse
import sys
import time
import json
import builtins
from argalias import ArgAlias

from rich import print_json, print
from rich.console import Console
from rich.table import Table

from pathlib import Path

from ..company import Company, CompanyList
from ..user import User
from ..fraud import detect, compare
from ..logger import loginit, logger, testlogger
from ..db import db
from ..const import SUMMARY_PERIOD

# CLI
from .summary import add_summary_parser, handle_summary
from .company import add_company_parser, handle_company
from .user import add_user_parser, handle_user
from .dev import add_dev_parser, handle_dev

last_summary = 0

def get_args():

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




def main():
    args = get_args()

    stopfile = Path('.stop')

    loginit("DEBUG" if args.verbose else "INFO")

    if args.subparser is None:
        if args.stop:
            stopfile.touch()

    if args.subparser == "summary":
        handle_summary(args)

    if args.subparser == "company":
        handle_company(args)

    elif args.subparser == "user":
        handle_user(args)

    elif args.subparser == "dev":
        handle_dev(args)
