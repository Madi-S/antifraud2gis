#!/usr/bin/env python3

import argparse
import sys
import time
from argalias import ArgAlias
from rich import print_json, print
from pathlib import Path
from dotenv import load_dotenv

from .company import Company, CompanyList
from .user import User
from .fraud import detect, compare
from .logger import loginit, logger, testlogger
from .db import db
from .const import SUMMARY_PERIOD


last_summary = 0

def get_args():

    aa = ArgAlias()
    aa.alias(["company"], "c")
    aa.alias(["company", "compare"], "cmp")
    aa.alias(["company", "fraud"], "f", "fr")
    aa.alias(["company", "reviews"], "rev")

    aa.alias(["user"], "u", "users")
    aa.alias(["user", "company"], "c", "ci")
    aa.alias(["user", "reviews"], "rev")
    aa.skip_flags()
    aa.parse()

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", default=False, action='store_true')
    parser.add_argument("--dump", default=False, action='store_true')
    parser.add_argument("--summary", default=False, action='store_true')
    parser.add_argument("--stop", default=False, action='store_true')

    # add subparser for company
    subparsers = parser.add_subparsers(dest="subparser", help="sub-command help")
    company_parser = subparsers.add_parser("company", help="info/operations about company")

    company_parser.add_argument("cmd", choices=["list", "info", "load", "load-user", "load-users", "fraud", "compare", "delete", "fraudfirst", "sum", 
                                                "summary", "setalias", "freeze", "unfreeze", "users", "reviews", "erasescore", "fixscore"])
    company_parser.add_argument("object_id", nargs='?', default=None)
    company_parser.add_argument("args", nargs=argparse.REMAINDER)

    user_parser = subparsers.add_parser("user", help="info/operations about users")
    user_parser.add_argument("cmd", choices=['info', 'company' , 'reviews'])
    user_parser.add_argument("uid")
    user_parser.add_argument("args", nargs=argparse.REMAINDER)


    return parser.parse_args()


def printsummary(cl: CompanyList):

    global last_summary

    userpath = Path(".storage/users")
    total = len(list(cl.companies()))    
    nerr = 0
    ncalc = 0
    nncalc = 0
    for c in cl.companies():
        if c.error:
            nerr += 1
            continue
        if c.score.get('NR') is None:
            nncalc += 1
            continue
        ncalc += 1

    logger.info(f"SUMMARY Companies: {total=}, {nerr=} {ncalc=} {nncalc=}")
    
    user_reviews_count = sum(1 for p in userpath.iterdir() if p.is_file())
    logger.info(f"SUMMARY Users with reviews: {user_reviews_count}")
    last_summary = time.time()



def main():
    args = get_args()

    stopfile = Path('.stop')

    load_dotenv()

    loginit("DEBUG" if args.verbose else "INFO")

    if args.subparser is None:
        if args.dump:
            db.dump()
        if args.stop:
            stopfile.touch()

    if args.subparser == "company":
        cmd = args.cmd
        cl = CompanyList()

        if args.object_id:
            try:
                company = cl[args.object_id]
            except (KeyError, AssertionError):
                company = None

        if cmd == "sum" or cmd == "summary":
            cl = CompanyList()
            printsummary(cl)

        elif cmd == "list":
            printsummary(cl)
            for c in cl.companies():
                c.load_reviews(local_only=True)
                print(" .. ", c)

        elif cmd == "info":
            if company is None:
                company = Company(args.object_id)
            company.load_reviews()
            print(company)

        elif cmd == "load":        
            company.load_reviews()
            print(company)

        elif cmd == "load-users":
            company.load_users()
            print(company)

        elif cmd == "fraud":
            if company is None:
                company = Company(args.object_id)

            detect(company, cl)
        elif cmd == "delete":
            company.delete()

        elif cmd == "fraudfirst":
            oid = db.get_suspicious_company()
            if oid is None:
                print("no suspicious companies")
                time.sleep(60)
                sys.exit(1)
            c = Company(oid)
            print("will check", c)
            detect(c, cl)

        elif cmd == "compare":
            cl = CompanyList()
            try:
                c2 = Company(args.args[0])
            except IndexError:
                print("no second company")
                sys.exit(1)

            compare(company, c2)
        elif cmd == "setalias":
            print(f"set alias {args.args[0]!r} for {company}")
            company.alias = args.args[0]
            company.save_basic()
        elif cmd == "freeze":
            company.frozen = True
            company.save_basic()
            print(company)
        elif cmd == "unfreeze":
            company.frozen = False
            company.save_basic()
            print(company)
        elif cmd == "users":
            for u in company.users():
                print(u)
        elif cmd == "reviews":
            if company is None:
                company = Company(args.object_id)
            company.load_reviews()
            for r in company.reviews():
                print(r, r.text)
        elif cmd == "erasescore":
            if company:
                company.score = {}
                company.save_basic()
            elif args.object_id == "ALL":
                for c in cl.companies():
                    c.score = {}
                    c.save_basic()
        elif cmd == "fixscore":
            for idx, c in enumerate(cl.companies()):
                if time.time() > last_summary + SUMMARY_PERIOD:
                    printsummary(cl)

                if stopfile.exists():
                    print("Stopfile found, stopping")
                    stopfile.unlink()
                    break
                if c.score and 'WSS' in c.score:
                    # print("Score OK for", c)
                    # print(c.score)
                    continue
                elif c.error:
                    # print("Skip error", c)
                    continue
                else:
                    print("FIX SCORE", c)
                    detect(c=c, cl=cl)
                    if args.object_id != 'ALL':
                        return
            
        else:
            print("no command", cmd)

    elif args.subparser == "user":
        u = User(args.uid)
        cmd = args.cmd

        if cmd == "info":
            print(u)
        elif cmd == "company":
            ci = u.get_company_info(args.args[0])
            print_json(data=ci)
        elif cmd == "reviews":
            for r in u.reviews():
                print(r)
        else:
            print("Unknown command", cmd)