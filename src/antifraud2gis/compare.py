import os
import sys
import numpy as np

from .company import Company
from .user import get_user
from .db import db

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
        u = get_user(uid)
        u.load()

        if uid in debug_uids:
            print(f"USER: {u}")

        for r in u.reviews():
            if r.oid == a.object_id:
                if r.uid in debug_uids:
                    if r not in aset:
                        print(f"aset add: {r}")

                aset.add(uid)
            if r.oid == b.object_id:
                if r.uid in debug_uids:
                    if r not in bset:
                        print(f"bset add: {r}")
                bset.add(uid)

    reviews_for_user = list()

    ab = aset & bset
    n_private = 0

    user_ages_a=list()
    user_ages_b=list()

    a_oldest = None
    a_newest = None
    b_oldest = None
    b_newest = None

    printn = 0
    for uid in ab:
        if db.is_private_profile(uid):
            n_private += 1
            continue

        u = get_user(uid)
        reviews_for_user.append(u.nreviews())
        #ar = u.review_for(a.object_id)
        #br = u.review_for(b.object_id)

        # review could be missing either from user (if private) or company (if hit reviews limit)
        arev = a.review_from(uid) or u.review_for(a.object_id)
        brev = b.review_from(uid) or u.review_for(b.object_id)

        user_ages_a.append(arev.user_age)
        user_ages_b.append(brev.user_age)

        if a_oldest is None or arev.created < a_oldest:
            a_oldest = arev.created
        if a_newest is None or arev.created > a_newest:
            a_newest = arev.created 
        
        if b_oldest is None or brev.created < b_oldest:
            b_oldest = brev.created
        if b_newest is None or brev.created > b_newest:
            b_newest = brev.created

        if arev is None or brev is None:
            print(f"ERROR: {u} {arev} {brev}")            
            sys.exit(1)

        if arev:
            aratings.append(arev.rating)
        if brev:
            bratings.append(brev.rating)

        
        printn += 1
        print(f"{printn}: {arev.rating}/{brev.rating} age:{arev.user_age}/{brev.user_age} {u}")
        # print(f"  {u.birthday_str} {arev.created_str} {brev.created_str}")
            
    aavg = round(float(np.mean(aratings)), 2)
    bavg = round(float(np.mean(bratings)), 2)

    print("--")
    print(f"common: {len(ab)} users, private: {n_private}")
    print(f"reviews: {len(reviews_for_user)}")
    print(f"mean num reviews: {round(float(np.mean(reviews_for_user)), 2)} median: {round(float(np.median(reviews_for_user)),3)}")
    print(f"avg rating {a.get_title()}: {aavg} avg raging {b.get_title( )}: {bavg}")
    print(f"User ages for A mean: {int(np.mean(user_ages_a))} median: {int(np.median(user_ages_a))}")
    print(f"User ages for B mean: {int(np.mean(user_ages_b))} median: {int(np.median(user_ages_b))}")
    print(f"A reviews: {a_oldest.strftime('%Y-%m-%d')} .. {a_newest.strftime('%Y-%m-%d')}")
    print(f"B reviews: {b_oldest.strftime('%Y-%m-%d')} .. {b_newest.strftime('%Y-%m-%d')}")

