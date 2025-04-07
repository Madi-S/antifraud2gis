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
from .user import User
from .relation import RelationDict, _is_dangerous
from .settings import settings
from .exceptions import AFReportNotReady

def compare(a: Company, b: Company):

    debug_oids = os.getenv("DEBUG_OIDS", "").split(" ")
    debug_uids = os.getenv("DEBUG_UIDS", "").split(" ")


    a.load_reviews()
    b.load_reviews()

    print("A:", a)
    print("B:", b)
    print("--")

    common = 0

    aset = set()
    bset = set()

    aratings = list()
    bratings = list()

    """ fill sets for a/b based on company reviews BUT often user is not found there (because not in first 500 reviews or other reason) """
    for r in a.reviews():
        if r.uid is None:
            continue
        if r.uid in debug_uids:
            print(f"bset1 add: {r}")
        aset.add(r.uid)

    for r in b.reviews():
        if r.uid is None:
            continue
        if r.uid in debug_uids:
            print(f"aset1 add: {r}")
        bset.add(r.uid)

    """ add a/b set from users's reviews (not company's reviews) """
    for uid in aset | bset:
        u = User(uid)
        u.load()

        if uid in debug_uids:
            print(f"USER: {u}")

        for r in u.reviews():
            if r.oid == a.object_id:
                if r.uid in debug_uids:
                    print(f"aset add: {r}")

                aset.add(uid)
            if r.oid == b.object_id:
                if r.uid in debug_uids:
                    print(f"bset add: {r}")
                bset.add(uid)


    reviews_for_user = list()

    ab = aset & bset
    n_private = 0

    for uid in ab:
        if db.is_private_profile(uid):
            n_private += 1
            continue

        u = User(uid)
        reviews_for_user.append(u.nreviews())
        #ar = u.review_for(a.object_id)
        #br = u.review_for(b.object_id)

        # review could be missing either from user (if private) or company (if hit reviews limit)
        ar = a.review_from(uid) or u.review_for(a.object_id)
        br = b.review_from(uid) or u.review_for(b.object_id)

        if ar is None or br is None:
            print(f"ERROR: {u} {ar} {br}")            
            sys.exit(1)

        if ar:
            aratings.append(ar.rating)
        if br:
            bratings.append(br.rating)

        
        print(f"{u} a:{ar.rating} b:{br.rating}")

            
    aavg = round(float(np.mean(aratings)), 2)
    bavg = round(float(np.mean(bratings)), 2)

    print(f"common: {len(ab)} users, private: {n_private}")
    print(f"reviews: {len(reviews_for_user)}")
    print(f"mean num reviews: {round(float(np.mean(reviews_for_user)), 2)} median: {round(float(np.median(reviews_for_user)),3)}")
    print(f"avg rating {a.get_title()}: {aavg} avg raging {b.get_title( )}: {bavg}")




def detect(c: Company, cl: CompanyList, force=False):

    debug_oids = os.getenv("DEBUG_OIDS", "").split(" ")
    debug_uids = os.getenv("DEBUG_UIDS", "").split(" ")

    if c.report_path.exists() and not force:
        print(f"SKIP because exists {c.report_path}")
        return

    c.relations = RelationDict(c)

    start = time.time()

    if c.error:
        print("error")
        print(c)
        print(c.error)
        return

    c.load_reviews()
    c.load_users()
    logger.info(f"Run fraud detect for {c.title} ({c.address}) {c.object_id} {c.nreviews()} reviews")

    c_hits = defaultdict(int)
    c_weight = defaultdict(int)

    processed_users = 0
    skipped_users = 0
    processed_reviews = 0

    skipped_users_ratings = list()

    # We should have our own numbers/per reviews list to catch users with 1 review. Relations will not catch it.
    nrlist = list()


    """
        with Progress() as progress:
            task = progress.add_task("[cyan]Loading user's reviews...", total=len(self._reviews))

            for idx, r in enumerate(self._reviews):
                progress.update(task, advance=1, description=f"[green]User {idx}")
                upid = r['user']['public_id']
    """


    with Progress() as progress:
        task = progress.add_task("[cyan]Analyzing user's reviews...", total=c.nreviews())

        for idx, cr in enumerate(c.reviews()):
            progress.update(task, advance=1, description=f"[green]User {idx}")
            if cr.age > settings.max_review_age:
                # too old review, safely skip it
                # print("Skip review", cr)
                continue

            if cr.uid is None:
                # print("!! Skip review without user", cr)
                skipped_users += 1
                skipped_users_ratings.append(cr.rating)
                continue
            u = cr.user

            nrlist.append(u.nreviews())

            if u.public_id in debug_uids:
                print(f"!! DEBUG: {u}")

            if u.nreviews():
                if u.public_id in debug_uids:
                    print(f"!! DEBUG: {u}")

                
                if u.nreviews() > MAX_USER_REVIEWS:
                    skipped_users += 1
                    skipped_users_ratings.append(cr.rating)
                    # print(f"Skip user {u} with {u.nreviews()} reviews")
                    continue

                # only for open profiles
                for r in u.reviews():

                    if not r.is_visible():
                        continue

                    if r.oid == c.object_id:
                        continue

                    # print("  review:", r)

                    rel = c.relations[r.oid]
                    rel.inc()
                    rel.add_user(u, cr.rating, r.rating)

                    c_hits[r.oid] += 1
                    c_weight[r.oid] += 1/u.nreviews()

                    #if r.oid in debug_oids:
                    #    print(f"{1/u.nreviews():.2f} {u}")

                    processed_reviews += 1

                processed_users += 1


    if False:
        if c.object_id in c_hits:
            del c_hits[c.object_id]
        if c.object_id in c_weight:
            del c_weight[c.object_id]

    c_weight = {k: v/c_hits[k] for k, v in c_weight.items()}

    wscore_sum = 0
    for _oid, score in c_weight.items():
        if score > WSCORE_THRESHOLD and c_hits[_oid] >= WSCORE_HITS_THRESHOLD:
            wscore_sum += score
    
    # print_json(data=c_weight[:5])

    n_neighbours = len(c_hits)

    if n_neighbours == 0:
        c.error = "no neighbours"
        c.save_basic()
        return

    neigh_review_ratio = n_neighbours / c.nreviews()
    
    # print(n_neighbours, c.nreviews())

    twin_score = 0
    for k, v in c_hits.items():
        twin_score += v - 1

    # print(f"HITS (rev:{c.nreviews()} / neigh:{n_neighbours})")
    

    

    c.relations.calc()

    trusted_ratings = list()
    tr_c = 0
    untr_c = 0
    for cr in c.reviews():
        if cr.uid is not None and cr.uid not in c.relations.dangerous_users:
            trusted_ratings.append(cr.rating)
            tr_c +=1 
        else:
            untr_c +=1

    # print(f"{tr_c=}, {untr_c=}")

    """
    nrel = 0
    nhits = 0
    nrel_high_ratings = 0
    nrel_high_hits = 0
    for rel in c.relations.relations.values():
        nhits+= rel.count
        if rel.check_high_hits():
            nrel += 1
            if rel.check_high_ratings():
                nrel_high_ratings += 1
                nrel_high_hits += rel.count
    """
    

    low_nrlist = list(filter(lambda x: x <= settings.risk_median_rpu, nrlist))

    score = dict()

    score['NR'] = round(neigh_review_ratio,3)
    score['TwinScore'] = round(twin_score/n_neighbours,3)
    score['WSS'] = round(wscore_sum,3)
    score['DoubleMedian'] = int(c.relations.doublemedian)
    score['NDangerous'] = c.relations.ndangerous
    score['total_users'] = processed_users + skipped_users 
    score['empty_user_ratio'] = int(100 * skipped_users / (processed_users + skipped_users))        
    score['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score['param_fp'] = settings.param_fp()
    score['median_reviews_per_user'] = round(float(np.median(nrlist)), 1)

    # score['nrel_high_ratings'] = nrel_high_ratings
    # score['highrate_relations'] = int(100*nrel / nrel_high_ratings) if nrel_high_ratings > 0 else 0
    # score['highrate_hits'] = int(nrel_high_hits / nrel) if nrel > 0 else 0


    if skipped_users_ratings:
        score['empty_user_avg_rate'] = round(float(np.mean(skipped_users_ratings)), 2)
    else:
        score['empty_user_avg_rate'] = None


    # c.score['full_rate'] = c.count_rate()
    # c.score['trusted_rate'] = round(float(np.mean(trusted_ratings)),2)

    # make verdict
    if score['empty_user_ratio'] > settings.risk_empty_user_ratio:
        score['trusted'] = False
        score['reason'] = f"empty_user_ratio {score['empty_user_ratio']}% ({skipped_users}/{processed_users + skipped_users}) ({score['empty_user_avg_rate']})"
    elif c.relations.nrisk_users > settings.risk_user_ratio:
        score['trusted'] = False
        score['reason'] = f"risk_users {c.relations.nrisk_users}"
    elif score['median_reviews_per_user'] <= settings.risk_median_rpu:
        score['trusted'] = False
        score['reason'] = f"median_reviews_per_user {score['median_reviews_per_user']} <= {settings.risk_median_rpu} ({len(low_nrlist)} of {len(nrlist)} are <= {settings.risk_median_rpu})"
    else:
        score['trusted'] = True

    # logger.info(f"SCORE: {score} for {c.object_id}")


    report = dict()
    report['score'] = score
    report['relations'] = c.relations.export()

    with gzip.open(c.report_path, "wt") as fh:
        json.dump(report, fh)

    c.save_basic()



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

        if _is_dangerous(avg_arating=rel['arating'], avg_brating=rel['brating'], count=rel['hits'], median=rel['median']):
            tags_cell = Text(f"{rel['tags'] or ''}*")
        else:
            tags_cell = rel['tags']

        if rel['hits'] > settings.risk_hit_th:
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
