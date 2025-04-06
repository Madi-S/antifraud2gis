import json
from loguru import logger
import time
import sys
import gzip
import traceback
import numpy as np
from rich.progress import Progress

from .settings import settings
from .const import DATAFORMAT_VERSION, SLEEPTIME, WSS_THRESHOLD, LOAD_NREVIEWS, REVIEWS_KEY
from .user import User
from .review import Review
from .session import session
from .exceptions import AFNoCompany

# to avoid circular import
class RelationDict:
    pass

class Company:

    relations: RelationDict

    def __init__(self, object_id):
        assert object_id is not None
        assert object_id.isdigit()

        self.object_id = object_id
        self.reviews_path = settings.company_storage / (object_id + '-reviews.json.gz')
        self.basic_path = settings.company_storage / (object_id + '-basic.json.gz')
        self.report_path = settings.company_storage / (object_id + '-report.json.gz')

        self._reviews = list()
        
        # basic info
        self.title = None
        self.alias = None
        self.remark = None
        self.address = None

        self.error = None

        self.tags = None

        self.rate = None


        # ratings
        # self.score = dict()
        # self.score['NR'] = None
        # self.score['TwinScore'] = None
        # self.score['WSS'] = None

        self.frozen = False

        self.load_basic()
        self.relations = None

    @staticmethod
    def wipe(object_id: str):
        assert object_id.isdigit()
        # wipe everything for company
        filelist =  [ 
            settings.company_storage / (object_id + '-reviews.json.gz'),
            settings.company_storage / (object_id + '-basic.json.gz'),
            settings.company_storage / (object_id + '-report.json.gz') 
            ]
        
        for f in filelist:
            if f.exists():
                print("unlink", f)
                f.unlink()




    def load_basic(self):
        if not self.load_basic_from_disk():            
            self.load_basic_from_network()
            self.save_basic()
        
    def set_tag(self, tag):
        self.tags = tag
        self.save_basic()

    def load_basic_from_disk(self):
        if self.basic_path.exists():
            with gzip.open(self.basic_path, "rt") as f:
                try:
                    _basic = json.load(f)
                except json.JSONDecodeError:
                    print("Cannot parse JSON!")
                    print(self.basic_path)
                    sys.exit(1)

                version = int(_basic.get('version', 0))
                if version != DATAFORMAT_VERSION:
                    logger.debug(f"version mismatch {version} != {DATAFORMAT_VERSION} for {self.object_id}")
                    return False

                self.title = _basic['title']
                self.alias = _basic['alias']
                self.remark = _basic['remark']
                self.address = _basic.get('address')
                self.version = _basic.get('version', 0)
                # self.score = _basic.get('score', dict())
                self.error = _basic.get('error', None)
                self.frozen = _basic.get('frozen', False)
                self.tags = _basic.get('tags', None)
                if not self.title:
                    logger.debug(f"no title for {self.object_id}")
                return bool(self.title)
        else:
            logger.debug(f"no file on disk for {self.object_id}")
            return False


    def save_basic(self):
        with gzip.open(self.basic_path, 'wt') as f:
            basic = {
                'version': DATAFORMAT_VERSION,
                'title': self.title, 
                'alias': self.alias,
                'remark': self.remark,
                'address': self.address,
                # 'score': self.score,
                'error': self.error,
                'frozen': self.frozen
            }
            if self.tags:
                basic['tags'] = self.tags
            json.dump(basic, f)


    def load_reviews(self, local_only=False):
        if self._reviews:
            return
        
        if self.reviews_path.exists():
            with gzip.open(self.reviews_path, "rt") as f:
                # print(f"Load company reviews from {self.reviews_path} mtime: {int(self.reviews_path.stat().st_mtime)} sz: {self.reviews_path.stat().st_size}")
                self._reviews = json.load(f)
                self.count_rate()
        else:
            if not local_only:
                self.load_reviews_from_network()
        return len(self._reviews)

    def count_rate(self):
        self.ratings = list()
        for r in self._reviews:
            self.ratings.append(r['rating'])

        if self.ratings:        
            self.rate = round(float(np.mean(self.ratings)), 2)
        return(self.rate)

    def users(self):
        for r in self._reviews:
            uid = r['user']['public_id']
            if uid is None:
                continue
            yield User(uid)

    def uids(self):
        for r in self._reviews:
            uid = r['user']['public_id']
            if uid is None:
                continue
            yield uid

    def load_users(self):
        self.load_reviews()
        # print(f"load users from {len(self._reviews)} reviews")
        with Progress() as progress:
            task = progress.add_task("[cyan]Loading user's reviews...", total=len(self._reviews))

            for idx, r in enumerate(self._reviews):
                progress.update(task, advance=1, description=f"[green]User {idx}")
                upid = r['user']['public_id']

                if upid is None:
                    # print("skip: no public_id", r['user']['name'])
                    continue

                logger.debug(f"Loading user {r['user']['name']} {upid} ({idx+1}/{len(self._reviews)})")
                user = User(upid)
                user.load()

    def load_reviews_from_network(self):
        url = f'https://public-api.reviews.2gis.com/2.0/branches/{self.object_id}/reviews?limit=50&fields=meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified&without_my_first_review=false&rated=true&sort_by=friends&key={REVIEWS_KEY}&locale=ru_RU'
        unused_geo = f'https://public-api.reviews.2gis.com/2.0/geo/141373143684284/reviews?limit=50&fields=meta.providers,meta.geo_rating,meta.geo_reviews_count,meta.total_count,reviews.hiding_reason&sort_by=friends&without_my_first_review=false&key={REVIEWS_KEY}&locale=ru_RU'

        page=0
        while url:
            logger.debug(f".. load reviews p{page} for {self}: {url}")
            r = session.get(url)
            #print(r.status_code)
            #print(r)
            #print(r.text)

            if r.status_code == 400:
                print("bad request", url)
                self.save_basic()
                break

            r.raise_for_status()
            data = r.json()
            total_count = data['meta']['total_count']            
            branch_reviews_count = data['meta']['branch_reviews_count']
            if total_count == 0 or branch_reviews_count == 0:                
                raise AFNoCompany(f"No reviews for {self.object_id}")

            self._reviews.extend(data['reviews'])
            url = data['meta'].get('next_link')
            time.sleep(SLEEPTIME)

            if len(self._reviews) >= LOAD_NREVIEWS:
                print(f"max reviews {len(self._reviews)} reached")
                break

            page+=1
        

        logger.info(f"Company {self.object_id}: loaded {len(self._reviews)} reviews")
        # why we were called?
        # print("----------")
        # print("".join(traceback.format_stack(limit=10)))         

        self.count_rate()

        with gzip.open(self.reviews_path, 'wt') as f:
            json.dump(self._reviews, f)


    def risk(self):
        if not self.score:
            return None
        
        if self.score.get('WSS') is None:
            return None

        if self.score['WSS'] > WSS_THRESHOLD:
            return True

        return False


    def __repr__(self):

        if self.error:
            return f'Company({self.object_id} {self.title!r} ERR:{self.error})'
   
        titlestr = f"{self.title!r} [{self.alias}]" if self.alias else repr(self.title)

        tags = " "
        if self.frozen:
            tags += "[FROZEN]"

        return f'Company({self.object_id} rate:{self.rate} {titlestr} addr: {self.address} reviews:{len(self._reviews) if self._reviews else "not loaded"}{tags})'

    def get_title(self):
        return self.title or self.object_id

    def get_town(self):
        if self.address is None:
            return None
        return self.address.split(',')[0]

    def export(self):
        self.load_reviews()
        data = {
            'oid': self.object_id,
            'title': self.title,
            'alias': self.alias,
            'address': self.address,
            'score': self.score,
            'nreviews': self.nreviews(),            
        }
        return data

    def reviews(self):
        for r in self._reviews:
            yield Review(r)
    
    def nreviews(self):
        return len(self._reviews)


    def load_basic_from_network(self):

        # print("load_basic", self.object_id)
        # print(self.title, self.address, "err:",self.error)

        self.load_reviews()
        for idx, r in enumerate(self._reviews):
            upid = r['user']['public_id']
                        
            if upid is None:
                # print("skip: no public_id", r['user']['name'])
                continue

            logger.debug(f"Loading user {r['user']['name']} {upid} ({idx+1}/{len(self._reviews)})")
            user = User(upid)
            user.load()
            ci = user.get_company_info(self.object_id)
            if ci is None:
                # print(f"no company info for me {self.object_id}, process next user")
                continue

            # print(f"found company info for me {self.object_id} in user {user}")
            self.title = ci['name']
            self.address = ci['address']
            return

    def delete(self):
        # delete all files about company
        if self.reviews_path.exists():
            self.reviews_path.unlink()
        if self.basic_path.exists():
            self.basic_path.unlink()

class CompanyList():
    path = None
    def __init__(self, path=None):
        self.path = path or settings.company_storage
    
    def __getitem__(self, index):
        basicpath = self.path / f'{index}-basic.json.gz'
        if basicpath.exists():
            logger.debug(f"Found company {index} by ID")
            return Company(index)
        
        # not found, try by alias
        for c in self.companies():
            if c.alias is None:
                continue
            if c.alias == index:
                logger.debug(f"Found company {index} by alias")
                return c
        raise KeyError(f"Company {index} not found")


    def companies(self, town = None):
        for f in self.path.glob('*-basic.json.gz'):
            oid = f.name.split('-')[0]
            c = Company(oid)        
            if town:                
                # filter by town
                town = town.lower()
                ctown = c.get_town()
                if ctown is None:
                    continue
                ctown = ctown.lower()
                if town != ctown:
                    continue
            yield c
    

    def company_exists(self, oid):
        basicpath = self.path / f'{oid}-basic.json.gz'
        return basicpath.exists()

    def getdesc(self, oid):
        if self.company_exists(oid):
            return str(Company(oid))
        else:
            return oid
    