from collections import defaultdict
import json
import os
from rich import print_json
import time
import datetime
import numpy as np


from .db import db
from .const import WSCORE_THRESHOLD, WSCORE_HITS_THRESHOLD, MAX_USER_REVIEWS
from .logger import logger
from .company import Company, CompanyList
from .user import User
from .relation import RelationDict
from .settings import settings

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
    for uid in ab:
        u = User(uid)
        reviews_for_user.append(u.nreviews())
        ar = u.review_for(a.object_id)
        br = u.review_for(b.object_id)

        aratings.append(ar.rating)
        bratings.append(br.rating)

        print(f"{u} a:{ar.rating} b:{br.rating}")

            
    aavg = round(float(np.mean(aratings)), 2)
    bavg = round(float(np.mean(bratings)), 2)

    print(f"common: {len(ab)} users")
    # print(f"reviews: {reviews_for_user}")
    print(f"mean num reviews: {round(float(np.mean(reviews_for_user)), 2)} median: {round(float(np.median(reviews_for_user)),3)}")
    print(f"avg rating {a.get_title()}: {aavg} avg raging {b.get_title( )}: {bavg}")




def detect(c: Company, cl: CompanyList):

    debug_oids = os.getenv("DEBUG_OIDS", "").split(" ")
    debug_uids = os.getenv("DEBUG_UIDS", "").split(" ")

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

    for cr in c.reviews():
        if cr.uid is None:
            # print("!! Skip review without user", cr)
            skipped_users += 1
            skipped_users_ratings.append(cr.rating)
            continue
        u = cr.user

        if u.public_id in debug_uids:
            print(f"!! DEBUG: {u}")

        if u.nreviews():
            if u.public_id in debug_uids:
                print(f"!! DEBUG: {u}")

            
            if u.nreviews() > MAX_USER_REVIEWS:
                skipped_users += 1
                skipped_users_ratings.append(cr.rating)
                # logger.info(f"Skip user {u} with {u.nreviews()} reviews")
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

    #if not c.object_id in c_hits:
    #    print_json(data=c_hits)
    #    c.error = "unusual"
    #    c.save_basic()
    #    return

    if c.object_id in c_hits:
        print("QQQQ")
        del c_hits[c.object_id]
    if c.object_id in c_weight:
        print("QQQQQQQQQ")
        del c_weight[c.object_id]

    # special_oid = "141265769338187" # zoo
    special_oid = "141265769369691" # rshb


    #print(c_weight[special_oid])
    #print("divide by ", c_hits[special_oid])
    c_weight = {k: v/c_hits[k] for k, v in c_weight.items()}
    #print(c_weight[special_oid])

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

    c.score = dict()

    c.score['NR'] = round(neigh_review_ratio,3)
    c.score['TwinScore'] = round(twin_score/n_neighbours,3)
    c.score['WSS'] = round(wscore_sum,3)
    c.score['DoubleMedian'] = int(c.relations.doublemedian)
    c.score['NDangerous'] = c.relations.ndangerous
    c.score['total_users'] = processed_users + skipped_users 
    c.score['empty_user_ratio'] = int(100 * skipped_users / (processed_users + skipped_users))
    c.score['empty_user_avg_rate'] = round(float(np.mean(skipped_users_ratings)), 2)
    c.score['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.score['param_fp'] = settings.param_fp()
    # c.score['full_rate'] = c.count_rate()
    # c.score['trusted_rate'] = round(float(np.mean(trusted_ratings)),2)

    # make verdict
    if c.score['empty_user_ratio'] > settings.risk_empty_user_ratio:
        c.score['trusted'] = False
        c.score['reason'] = f"empty_user_ratio {c.score['empty_user_ratio']} ({c.score['empty_user_avg_rate']})"
    elif c.relations.nrisk_users > settings.risk_user_ratio:
        c.score['trusted'] = False
        c.score['reason'] = f"risk_users {c.relations.nrisk_users}"
    else:
        c.score['trusted'] = True

    logger.info(f"SCORE: {c.score} for {c.object_id}")

    c.save_basic()

    #print(f"{neigh_review_ratio=:.3f}")
    #print(f"{twin_score=} / {n_neighbours} = {twin_score/n_neighbours:.3f}")
    #print(f"{wscore_sum=:.3f}")


    # remove from c_hits all values 1
    # c_hits = {k: v for k, v in c_hits.items() if v > 1}

    # print c_hits keys ordered by value

    return

    c_hits_list = sorted(c_hits.items(), key=lambda x: x[1], reverse=True)
    print("")
    print("HITS:")
    for k,v in c_hits_list:
        if v<=10:
            break
        #_c = Company(k)
        #_c.load_reviews()
        # company_desc = cl.getdesc(k)
        _c = Company(k)
        print(f"{_c} hits: {v}")
        print("    ", c.relations[k])
    
    print()


    print("Weighted Scores:")
    for k,v in sorted(c_weight.items(), key=lambda x: x[1], reverse=True):
        if v<=WSCORE_THRESHOLD or c_hits[k] < WSCORE_HITS_THRESHOLD:
            if k in debug_oids:
                print(f"!! DEBUG: {k} {v:.3f} (< {WSCORE_THRESHOLD})  {c_hits[k]} (< {WSCORE_HITS_THRESHOLD})")
            continue
        # logger.debug(f"add suspicious company {k} with wscore {v:.3f} from {c}")
        # db.add_company_todo(k)
        _c = Company(k)

        print(f"{_c} h: {c_hits[k]} w: {c_weight[k]:.3f}")
        
    print(c.relations)

    print(f"# processed {processed_users} users {processed_reviews} reviews in {round(time.time() - start, ndigits=2)} sec")
    db.remove_company_todo(c.object_id)

