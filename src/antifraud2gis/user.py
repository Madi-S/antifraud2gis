from pathlib import Path
import requests
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import time
import functools
from rich.pretty import Pretty
from rich import print_json
import traceback
import sys
import datetime
import gzip
import lmdb
import tempfile
import os

from .db import db
from .const import WSS_THRESHOLD, LOAD_NREVIEWS, SLEEPTIME, LMDB_MAP_SIZE
from .settings import settings
from .statistics import statistics
from .session import session
from .review import Review
from .logger import logger

THRESHOLD_NR=3
THRESHOLD_TS=1.5

user_pool = dict()

def retry(max_attempts=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay)
            raise RuntimeError(f"Function {func.__name__} failed after {max_attempts} attempts")
        return wrapper
    return decorator


class User:
    def __init__(self, public_id):

        self.public_id = public_id
        self.reviews_path = settings.user_storage / (public_id + '-reviews.json.gz')
        self._reviews = list()
        self.load(local_only=True)

    def lmdb_load(self, local_only=False):
        # prepare data structures
        objects = dict()
        reviews = list()

        # print("ZZZ lmdb_load", self.public_id, local_only)
        # print("".join(traceback.format_stack(limit=10)))
        
        env = lmdb.open(settings.lmdb_storage.as_posix(), map_size=LMDB_MAP_SIZE)

        with env.begin() as txn:
            val = txn.get(b"user:" + self.public_id.encode())
            if val:
                self._reviews = json.loads(val)
                return

            # not found in db
            if local_only is False:                
                loaded = False
                while not loaded:
                    try:
                        self.load_from_network()
                        loaded = True
                    except Exception as e:
                        print(f"Error loading user {self.public_id}: {type(e)} {e}")
                        time.sleep(5)



    def load(self, local_only=False):
        return self.lmdb_load(local_only=local_only)

    def old_load(self, local_only=False):
        if self._reviews:
            # already loaded
            return
        
        if self.reviews_path.exists():
            with gzip.open(self.reviews_path, "rt") as f:
                try:
                    self._reviews = json.load(f)
                except json.JSONDecodeError:
                    print("Cannot parse JSON!")
                    print(self.reviews_path)
                    sys.exit(1)
        else:
            if local_only is False:
                loaded = False
                while not loaded:
                    try:
                        self.load_from_network()
                        loaded = True
                    except Exception as e:
                        print(f"Error loading user {self.public_id}: {e}")
                        time.sleep(5)

    def lmdb_save(self, reviews: list, txn = None):        
        """ """

        def save_txn():
            # logger.debug(f'lmdb save user {self.public_id}: {reviews}')
            txn.put(b'user:' + self.public_id.encode(), json.dumps(data_reviews).encode())

            for oid, odata in objects.items():
                # logger.debug(f'lmdb save object {oid}: {odata}')
                txn.put(b'object:' + oid.encode(), json.dumps(odata).encode(), overwrite=False)


        # prepare data structures
        objects = dict()
        data_reviews = list()

        for r in reviews:
            # update objects
            objects[r['object']['id']] = {
                'name': r['object']['name'],
                'address': r['object']['address']
            }

            created = datetime.datetime.strptime(r['date_created'].split('T')[0], "%Y-%m-%d")

            data_reviews.append({
                'rating': r['rating'],
                'oid': r['object']['id'],
                'uid':  r['user']['public_id'],
                'user_name':  r['user']['name'],
                'provider': r['provider'],
                'created': created.strftime("%Y-%m-%d")
            })

        if txn:
            save_txn()
        else:
            env = lmdb.open(settings.lmdb_storage.as_posix(), map_size=LMDB_MAP_SIZE)

            with env.begin(write=True) as txn:
                save_txn()

    def nreviews(self):
        self.load()
        return len(self._reviews)

    def birthday(self):
        self.load()
        if not self._reviews:
            # private profile
            return None
        try:
            r = Review(sorted(self._reviews, key=lambda r: r['created'])[0])
        except KeyError:
            print_json(data=self._reviews)
            raise
        return r.created

    def towns(self):
        self.load()
        towns = set()
        for r in self.reviews():
            # print_json(data=r)
            towns.add(r.oid)
        return towns

    @property
    def birthday_str(self):
        return self.birthday().strftime("%Y-%m-%d")

    def get_company_info(self, oid):
        self.load()
        for r in self.reviews():
            if r.oid == oid:
                print_json(data = r._data)
                if 'object' in r._data:
                    return r._data['object']


    def reviews(self):
        self.load()
        # reviews are sorted by date_edited desc, not by date_created, we need to re-sort
        for r in sorted(self._reviews, key=lambda r: r['created']):
            if r['oid'] in settings.skip_oids:
                continue
            yield Review(r, user=self)

    def review_for(self, oid: str) -> Review:
        for r in self.reviews():
            if r.oid == oid:
                return r

    def load_from_network(self):

        if db.is_private_profile(self.public_id):
            # logger.debug("skip: private profile from shelf", self.public_id)
            return

        # print(f"  # load (network) reviews for user {self.public_id}")

        # why we were called?
        # print("".join(traceback.format_stack(limit=10))) 

        url = f'https://api.auth.2gis.com/public-profile/1.1/user/{self.public_id}/content/feed?page_size=20'

        page = 0

        _reviews = list()

        while True:
            logger.debug(f"Loading user reviews p{page} for user {self} from {url}")
            time.sleep(SLEEPTIME)
            r = session.get(url)
            if r.status_code == 403:
                # print("New private profile", self.public_id)
                db.add_private_profile(self.public_id)
                return
            elif r.status_code in [400, 500]:
                logger.warning(f"user {self} reviews error {r.status_code} url: {url}")
                break
            else:
                r.raise_for_status()
          
            data = r.json()

            for el in data['content_feed']:
                try:
                    review = el['review']
                except KeyError:
                    continue
                _reviews.append(review)


            # self.reviews.extend(data['reviews'])

            # prepare next page url
            try:
                token = data['next_page_token']                
            except KeyError:
                # logger.debug("no token in response")
                break

            # logger.debug(f"token: {token}")
            


            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            query_params['page_token'] = token
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse(parsed_url._replace(query=new_query))
            page+=1


        # print(f"user {self.name} loaded {len(self._reviews)} reviews")
        # print("save to", self.reviews_path)
        #with gzip.open(self.reviews_path, 'wt') as f:
        #    json.dump(self._reviews, f)
        try:
            self.lmdb_save(reviews=_reviews)
        except Exception as e:
            print(f"Error saving user {self.public_id}: {e}")            
            sys.exit(1)

        # now we can load from database
        self.load()
        statistics.total_users_loaded_network += 1
        statistics.total_users_loaded += 1

    @property
    def url(self):
        return f"https://2gis.ru/af2gis/user/{self.public_id}"

    @property
    def name(self):
        if self._reviews:

            try:
                return self._reviews[0]['user_name']
            except KeyError:
                return None
            # return self._reviews[0]['user']['name']
        else:
            return None

    @staticmethod
    def users():
        env = lmdb.open(settings.lmdb_storage.as_posix(), readonly=True, map_size=LMDB_MAP_SIZE, lock=False)
        prefix = b'user:'
        key = prefix  # start with first 'user:'

        while True:
            with env.begin() as txn:  # making lot of very SHORT transactions
                with txn.cursor() as cur:
                    if not cur.set_range(key):  
                        return  # The End
                    for k, _ in cur:
                        if not k.startswith(prefix):  # Wrong key. no more users:, the End
                            return
                        public_id = k.decode().split(':', 1)[1]  
                        yield User(public_id)  
                        key = k + b'\x00'  # will use next key
                        break 


    @staticmethod
    def old_users_file():
        env = lmdb.open(settings.lmdb_storage.as_posix(), readonly=True, map_size=LMDB_MAP_SIZE, lock=False)
        prefix = b'user:'

        with tempfile.NamedTemporaryFile(mode='w+', prefix='af2gis-users-', suffix='.txt', delete=False) as f:
            tmp_path = f.name
            print(f"Userlist in {tmp_path}")
            with env.begin() as txn:
                with txn.cursor() as cur:
                    if cur.set_range(prefix):
                        for key, _ in cur:
                            if not key.startswith(prefix):
                                break
                            public_id = key.decode().split(':', 1)[1]
                            f.write(public_id + '\n')

        try:
            with open(tmp_path, 'r') as f:
                for line in f:
                    yield User(line.strip())
        finally:
            os.remove(tmp_path)


    @staticmethod
    def old_users_iterator():
        #for file in settings.user_storage.glob('*-reviews.json.gz'):
        #    yield User(file.stem.split('-')[0])
        env = lmdb.open(settings.lmdb_storage.as_posix(), readonly=True, map_size=LMDB_MAP_SIZE)
        with env.begin() as txn:
            with txn.cursor() as cur:
                if cur.set_range(b'user:'):
                    for key, value in cur:
                        if not key.startswith(b'user:'):
                            break
                        public_id = key.decode().split(':')[1]
                        yield User(public_id)


    @staticmethod
    def nusers():
        n = 0
        env = lmdb.open(settings.lmdb_storage.as_posix(), readonly=True, map_size=LMDB_MAP_SIZE)
        with env.begin() as txn:
            with txn.cursor() as cur:
                if cur.set_range(b'user:'):
                    for key, value in cur:
                        if not key.startswith(b'user:'):
                            break
                        n+=1
        return n


    def __repr__(self):
        return f'User({self.name} {self.url} rev: {len(self._reviews) if self._reviews else "not loaded"})'



def get_user(public_id: str) -> User:
    global user_pool
    if public_id not in user_pool:
        user_pool[public_id] = User(public_id)
        # print(f"new user {public_id}")
    return user_pool[public_id]

def reset_user_pool():
    global user_pool
    user_pool = dict()