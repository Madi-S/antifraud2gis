from collections import defaultdict
import json
import os
from rich import print_json
import time

from .db import db
from .const import WSCORE_THRESHOLD, WSCORE_HITS_THRESHOLD
from .logger import logger
from .company import Company, CompanyList
from .user import User



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


    ab = aset & bset
    for uid in ab:
        u = User(uid)
        print(u)
            
    print(f"common: {len(ab)} users")

def detect(c: Company, cl: CompanyList):

    debug_oids = os.getenv("DEBUG_OIDS", "").split(" ")
    debug_uids = os.getenv("DEBUG_UIDS", "").split(" ")


    start = time.time()

    if c.error:
        print(c)
        return
    c.load_reviews()
    c.load_users()
    logger.info(f"Run fraud detect for {c.title} ({c.address}) {c.nreviews()} reviews")

    c_hits = defaultdict(int)
    c_weight = defaultdict(int)

    processed_users = 0
    processed_reviews = 0


    for cr in c.reviews():
        if cr.uid is None:
            continue
        u = cr.user

        if u.public_id in debug_uids:
            print(f"!! DEBUG: {u}")

        if u.nreviews():
            # only for open profiles            
            for r in u.reviews():

                if not r.is_visible():
                    continue

                # print("  review:", r)
                c_hits[r.oid] += 1
                c_weight[r.oid] += 1/u.nreviews()
                processed_reviews += 1

                if r.oid in debug_oids and r.oid != c.object_id:
                    print(f"DEBUG: {c_hits[r.oid]} {u} {r}")


            processed_users += 1

    if not c.object_id in c_hits:
        print_json(data=c_hits)
        c.error = "unusual"
        c.save_basic()
        return

    del c_hits[c.object_id]
    del c_weight[c.object_id]

    c_weight = {k: v/processed_users for k, v in c_weight.items()}

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
    
    twin_score = 0
    for k, v in c_hits.items():
        twin_score += v - 1

    print(f"HITS (rev:{c.nreviews()} / neigh:{n_neighbours})")
    
    c.score['NR'] = round(neigh_review_ratio,3)
    c.score['TwinScore'] = round(twin_score/n_neighbours,3)
    c.score['WSS'] = round(wscore_sum,3)
    logger.info(f"SCORE: {c.score} for {c.object_id}")

    c.save_basic()
    #print(f"{neigh_review_ratio=:.3f}")
    #print(f"{twin_score=} / {n_neighbours} = {twin_score/n_neighbours:.3f}")
    #print(f"{wscore_sum=:.3f}")


    # remove from c_hits all values 1
    # c_hits = {k: v for k, v in c_hits.items() if v > 1}

    # print c_hits keys ordered by value
    c_hits_list = sorted(c_hits.items(), key=lambda x: x[1], reverse=True)
    print("")
    print("HITS:")
    for k,v in c_hits_list:
        if v<=10:
            break
        #_c = Company(k)
        #_c.load_reviews()
        company_desc = cl.getdesc(k)
        print(f"{company_desc} hits: {v}")
    print()


    print("Weighted Scores:")
    for k,v in sorted(c_weight.items(), key=lambda x: x[1], reverse=True):        
        if v<=WSCORE_THRESHOLD or c_hits[k] < WSCORE_HITS_THRESHOLD:
            break
        logger.debug(f"add suspicious company {k} with wscore {v:.3f} from {c}")
        db.add_company_todo(k)
        company_desc = cl.getdesc(k)
        print(f"{company_desc} h: {c_hits[k]} w: {c_weight[k]:.3f}")
        


    print(f"# processed {processed_users} users {processed_reviews} reviews in {round(time.time() - start, ndigits=2)} sec")
    db.remove_company_todo(c.object_id)
