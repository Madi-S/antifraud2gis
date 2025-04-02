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
import gzip

from .db import db
from .const import WSS_THRESHOLD, LOAD_NREVIEWS, SLEEPTIME
from .settings import settings
from .session import session
from .review import Review
from .logger import logger

THRESHOLD_NR=3
THRESHOLD_TS=1.5





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
        self.reviews_path = settings.user_storage / (public_id + '-reviews.json')
        self._reviews = list()
        self.load(local_only=True)

    def load(self, local_only=False):
        if self.reviews_path.exists():
            with gzip.open(self.reviews_path, "rt") as f:
                self._reviews = json.load(f)
        else:
            if local_only is False:
                self.load_from_network()

    def nreviews(self):
        self.load()
        return len(self._reviews)

    def get_company_info(self, oid):
        self.load()
        for r in self.reviews():
            if r.oid == oid:
                return r._data['object']

    def reviews(self):
        self.load()
        for r in self._reviews:
            yield Review(r)

    def review_for(self, oid: str) -> Review:
        for r in self.reviews():
            if r.oid == oid:
                return r

    def load_from_network(self):
        if db.is_private_profile(self.public_id):
            logger.debug("skip: private profile from shelf", self.public_id)
            return

        print(f"  # load (network) reviews for user {self.public_id}")

        # why we were called?
        # print("".join(traceback.format_stack(limit=10))) 

        url = f'https://api.auth.2gis.com/public-profile/1.1/user/{self.public_id}/content/feed?page_size=20'        

        page = 0

        while True:
            logger.debug(f"Loading page {page} for user {self}")
            time.sleep(SLEEPTIME)
            r = session.get(url)
            if r.status_code == 403:
                print("New private profile", self.public_id)
                db.add_private_profile(self.public_id)
                return
            elif r.status_code in [400, 500]:
                logger.warning(f"user {self} revied error {r.status_code} url: {url}")
                break
            else:
                r.raise_for_status()
          
            data = r.json()

            for el in data['content_feed']:
                try:
                    review = el['review']
                except KeyError:
                    continue
                self._reviews.append(review)


            # self.reviews.extend(data['reviews'])

            # prepare next page url
            try:
                token = data['next_page_token']                
            except KeyError:
                logger.debug("no token in response")
                break

            # logger.debug(f"token: {token}")
            


            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            query_params['page_token'] = token
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse(parsed_url._replace(query=new_query))
            page+=1


        print(f"user {self.name} loaded {len(self._reviews)} reviews")
        print("save to", self.reviews_path)
        with gzip.open(self.reviews_path, 'wt') as f:
            json.dump(self._reviews, f)

    @property
    def url(self):
        return f"https://2gis.ru/x/user/{self.public_id}"

    @property
    def name(self):
        if self._reviews:
            return self._reviews[0]['user']['name']
        else:
            return None


    def __repr__(self):
        return f'User({self.public_id} {self.name} (rev: {len(self._reviews) if self._reviews else "not loaded"}) {self.url})'
    
