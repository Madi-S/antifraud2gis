import argparse
import builtins
import json
import time
import sys
from rich import print as pprint, print_json
from rich.text import Text

from ..company import Company, CompanyList
from ..fraud import detect, compare, dump_report
from ..tasks import fraud_task
from ..exceptions import AFReportNotReady, AFNoCompany, AFNoTitle
from ..settings import settings
from .summary import printsummary
from ..user import reset_user_pool
from pathlib import Path

stopfile = Path('.stop')

def add_company_parser(subparsers):
    company_parser = subparsers.add_parser("company", help="info/operations about company")
    company_parser.add_argument("cmd", choices=["wipe", "submit", "list", "info", "export", "settag", "fraud", "compare", "delete", "fraud1", "fraudall", "sum", 
                                                "summary", "setalias", "freeze", "unfreeze", "users", "reviews", "erasescore", "fixscore",
                                                "reload", "report"])
    company_parser.add_argument("object_id", nargs='?', default=None)
    company_parser.add_argument("--show", "-s", type=int, default=settings.show_hit_th, help="override show_hit_th")
    company_parser.add_argument("-n", type=int, help="Process only N companies and quit")
    company_parser.add_argument("--town", "-t", help="Process only companies in this town")
    company_parser.add_argument("args", nargs='*')


    return company_parser


def handle_company(args: argparse.Namespace):
    cmd = args.cmd
    cl = CompanyList()
    
    if args.object_id:
        try:
            company = cl[args.object_id]
        except (KeyError, AssertionError):
            company = None

    if cmd == "export":            
        builtins.print(json.dumps(company.export(), indent=4, ensure_ascii=False))

    elif cmd == "info":
        if company is None:
            if args.object_id.isdigit():
                print("init new company")
                company = Company(args.object_id)            
                company.load_reviews()
            else:
                print("company not found")
                sys.exit(1)
        print(company)
    
    elif cmd == "list":
        for c in cl.companies(town=args.town):
            print(c)

    elif cmd == "submit":
        fraud_task.send(args.object_id)

    elif cmd == "wipe":
        print("wipe", args.object_id)
        Company.wipe(args.object_id)

    elif cmd == "fraud":

        if company is None:
            try:
                company = Company(args.object_id)
            except AFNoCompany:
                print("company not found")
                sys.exit(1)

        settings.show_hit_th = args.show

        detect(company, cl, force=True)
        dump_report(company.object_id)
        #company.relations.dump_table()
        #if company.score['trusted']:
        #    pprint(Text("Company is trusted", style='green'))
        #else:
        #    pprint(Text("Company is NOT trusted:", style='red'), f"({company.score['reason']})")
        # print_json(data=company.score)
        # dump_report(company.object_id)

    elif cmd == "report":
        if company is None:
            try:
                company = Company(args.object_id)
            except AFNoCompany:
                print("company not found (or no reviews)")
                sys.exit(1)
        try:                
            dump_report(company.object_id)
        except AFReportNotReady:
            print("report not ready")
            sys.exit(1)

    elif cmd == "delete":
        company.delete()
    elif cmd == "reload":
        if company:
            alias = company.alias
            company.delete()
            object_id = company.object_id
        else:
            alias = None
            object_id = args.object_id
        company = Company(object_id)
        company.load_basic_from_network()
        company.alias = alias
        company.save_basic()            
        company.load_reviews_from_network()


    elif cmd == "settag":
        company.set_tag(args.args[0])

    elif cmd == "fraud1":
        for c in cl.companies(town=args.town):
            if c.error:
                # print("skip error", c)
                continue
            if c.report_path.exists():
                # print("skip already reported", c)                
                continue
            print(c)
            detect(c, cl)
            dump_report(c.object_id)
            printsummary(cl)
            return

    elif cmd == "fraudall":
        processed = 0
        for idx, c in enumerate(cl.companies(town=args.town)):
            if c.error:
                # print("skip error", c)
                continue
            if c.report_path.exists():
                # print("skip already reported", c)                
                continue
            print(c)
            detect(c, cl)
            dump_report(c.object_id)
            reset_user_pool()
            processed += 1
            if idx % 10 == 0:
                printsummary(cl)
            if stopfile.exists():
                print("Stopfile found, stopping")
                stopfile.unlink()
                break
            if args.n and processed >= args.n:
                print(f"reached limit {processed} >= {args.n}")
                break            



    elif cmd == "compare":
        cl = CompanyList()
        try:
            c2 = cl[args.args[0]] # Company(args.args[0])
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
                fraud_print(c=c, cl=cl)
                if args.object_id != 'ALL':
                    return
        
    else:
        print("no command", cmd)

