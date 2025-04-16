from collections import defaultdict
import json
import os
from rich import print_json
from rich.console import Console
from rich.table import Table
from rich.text import Text
import time
import sys
import datetime
import numpy as np
import gzip
from rich.progress import Progress

from .db import db
from .const import WSCORE_THRESHOLD, WSCORE_HITS_THRESHOLD, MAX_USER_REVIEWS
from .logger import logger
from .company import Company, CompanyList
from .companydb import update_company, get_by_oid, check_by_oid
from .user import User, get_user
from .relation import RelationDict, _is_dangerous
from .settings import settings
from .exceptions import AFReportNotReady, AFNoCompany, AFReportAlreadyExists
# from .usernotes import Usernotes
from .fd.master import MasterFD
from .search import company_indexed, index_company

def detect(c: Company, cl: CompanyList, explain: bool = False, force=False):

    debug_oids = os.getenv("DEBUG_OIDS", "").split(" ")
    debug_uids = os.getenv("DEBUG_UIDS", "").split(" ")

    # notes = Usernotes()

    if c.report_path.exists() and not force and not explain:
        raise AFReportAlreadyExists(f"Report already exists: {c.report_path}")
        print(f"SKIP because exists {c.report_path}")
        # read 
        with gzip.open(c.report_path, "rt", encoding="utf-8") as f:
            result = json.load(f)  # Directly parse JSON
        return result['score']

    c.relations = RelationDict(c)

    start = time.time()

    if c.error:
        print("error")
        print(c)
        print(c.error)
        return

    c.load_reviews()
    c.load_users()

    """ skip too small targets """
    if c.nreviews() <= settings.min_reviews:
        # bypass
        score = {
            'trusted': True,
            'total_users': c.nreviews(),
            'reason': f'Too few reviews ({c.nreviews()}) to be fraudulent',
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        report = dict()        
        report['score'] = score
        report['relations'] = list()

        c.trusted = True
        c.detections = list()

        update_company(c.export())

        with gzip.open(c.report_path, "wt") as fh:
            json.dump(report, fh)
        
        return score
            # print("saved")

    logger.info(f"Run fraud detect for {c.title} ({c.address}) {c.object_id} {c.nreviews()} reviews")

    master_detector = MasterFD(c, explain=True)

    with Progress() as progress:
        task = progress.add_task("[cyan]Analyzing user's reviews...", total=c.nreviews())

        for idx, cr in enumerate(c.reviews(), start=1):
            # notes.counter('total_reviews')
            progress.update(task, advance=1, description=f"[green]User {idx}")

            master_detector.feed(cr)    

    score = master_detector.get_score()
    

    # logger.info(f"SCORE: {score} for {c.object_id}")

    report = dict()
    report['score'] = score
    report['relations'] = c.relations.export()

    with gzip.open(c.report_path, "wt") as fh:
        json.dump(report, fh)

    if not score['trusted']:
        print(f"save explain to {c.explain_path}")    
        with gzip.open(c.explain_path, "wt") as fh:            
            master_detector.explain(fh=fh)

    c.trusted = score['trusted']
    c.detections = [ dline.split(' ')[0] for dline in score['detections'] ]
    c.save_basic()

    print_json(data=score)

    update_company(c.export())

    logger.info(f"DETECTION RESULT {c}")
    return score


def dump_report(object_id: str):

    c = Company(object_id)
    if c.error:
        print(f"ERROR for {c.get_title()} ({c.address}): {c.error}")
        return

    try:
        print("read report from", c.report_path)
        with gzip.open(c.report_path, "rt") as fh:
            report = json.load(fh)
    except FileNotFoundError:
        raise AFReportNotReady(f"Report not ready for {object_id}")

    console = Console()
    table = Table(show_header=True, header_style="bold magenta", title=f"{c.get_title()} ({c.address}) {c.object_id}")
    table.add_column("T", style='red')
    table.add_column("Company name")
    table.add_column("Town")
    table.add_column("ID/Alias")
    table.add_column("Hits")
    #table.add_column("Mean")
    table.add_column("Median")
    table.add_column("Rating")

    for rel in report['relations']:
        _c = Company(rel['oid'])

        if rel['risk']:
            tags_cell = Text(f"{rel['tags'] or ''}*")
        else:
            tags_cell = rel['tags']

        if rel['hits'] >= settings.risk_hit_th:
            hits_cell = Text(f"{rel['hits']}", style='red')
        else:
            hits_cell = Text(str(rel['hits']), style="green")

        if rel['median'] < settings.risk_median_th:
            median_cell = Text(str(rel['median']), style='red')
        else:
            median_cell = Text(str(rel['median']), style='green')

        if rel['arating'] >= settings.risk_highrate_th and rel['brating'] >= settings.risk_highrate_th:
            rating_cell = Text(f"{rel['arating']:.1f} {rel['brating']:.1f}", style='red')
        else:
            rating_cell = Text(f"{rel['arating']:.1f} {rel['brating']:.1f}")

        table.add_row(tags_cell, _c.get_title(), _c.get_town(), _c.alias or Text(_c.object_id, style='grey30'), hits_cell,
                        # f"{rel.mean:.1f}", 
                        median_cell, rating_cell)
    print()
    console.print(table)
    print_json(data=report['score'])

    # rprint(self)
