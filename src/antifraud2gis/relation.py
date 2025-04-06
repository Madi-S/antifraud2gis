from .company import Company
from .settings import settings
from .exceptions import AFNoCompany
import os
import numpy as np

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import print as rprint

#risk_hit_th = int(os.getenv('RISK_HIT_TH', '10'))
#risk_median_th = int(os.getenv('RISK_MEDIAN_TH', '15'))
#show_hit_th = int(os.getenv('SHOW_HIT_TH', '11'))

# print(settings.risk_hit_th, settings.risk_median_th, settings.show_hit_th)

users_added = 0


def _is_dangerous(avg_arating, avg_brating, count, median, debug=False):
    # high-rate check
    if avg_arating >= settings.risk_highrate_th and avg_brating >= settings.risk_highrate_th:
        #if count >= settings.risk_highrate_hit_th and median <= settings.risk_highrate_median_th:
        #    return True
        # default check
        if count >= settings.risk_hit_th and median <= settings.risk_median_th:            
            return True
    
    return False
        


class Relation:
    """ relation between two companies """

    a: Company
    b: str
    _users: set
    nusers: int
    mean: float
    median: float
    avg_rating_a: float
    avg_rating_b: float

    count: int

    def __init__(self, a: Company, b: str):
        self.a = a
        self.b = b
        self.count = 0
        self._calculated = False
        self._users = set()
        self._aratings = list()
        self._bratings = list()
        self.nusers = 0
        self.mean = None
        self.median = None
        self.avg_arating = None
        self.avg_brating = None

    def add_user(self, user, a_rating, b_rating):
        global users_added
        if user in self._users:
            # print(f"ALREADY EXISTS {user} for {self.b}")
            pass
        self._users.add(user)
        self._aratings.append(a_rating)
        self._bratings.append(b_rating)
        self.nusers = len(self._users)
        users_added += 1

    def calc(self):
        if self._calculated:
            return

        user_reviews = list()

        for u in self._users:
            user_reviews.append(u.nreviews())

        if not user_reviews:
            print("no users for relation to", self.b)
            print("count:", self.count)
            return


        self.mean = round(float(np.mean(user_reviews)), 3)
        self.median = int(np.median(user_reviews))
        self.avg_arating = round(float(np.mean(self._aratings)), 3)
        self.avg_brating = round(float(np.mean(self._bratings)), 3)

        self._calculated = True

    def inc(self):
        self.count += 1
    
    def users(self):
        for u in self._users:
            yield u


    def is_dangerous(self, avg_arating=None, avg_brating=None, count=None, median=None):
        self.calc()
        
        return _is_dangerous(self.avg_arating, self.avg_brating, self.count, self.median)

        # high-rate check
        if self.avg_arating >= settings.risk_highrate_th and self.avg_brating >= settings.risk_highrate_th:
            if self.count >= settings.risk_highrate_hit_th and self.median <= settings.risk_highrate_median_th:
                return True

        # default check
        if self.count >= settings.risk_hit_th and self.median <= settings.risk_median_th:
            return True
        return False
    
    def __repr__(self):
        if not self._calculated:
            self.calc()
        bcompany = Company(self.b)
        return f"{bcompany.get_title()} ({bcompany.address}): hits: {len(self._users)}/{self.count} mean: {self.mean} median: {self.median})"

class RelationDict:

    c: Company
    relations: dict

    meanmedian: float
    doublemedian: float
    ndangerous: int
    nrisk_users: int

    nusers: int
    nreviews: int
    meanreviews: float
    medianreviews: float
    dangerous_users: list[str]

    

    def __init__(self, c: Company):
        self.c = c
        self.relations = dict()
        self.meanmedian = None
        self.doublemedian = None
        self.ndangerous = None
        self.dangerous_users = set()
        self.nrisk_users = None

    def __getitem__(self, oid) -> Relation:
        if oid not in self.relations:
            self.relations[oid] = Relation(self.c, oid)
        return self.relations[oid]

    def calc(self):        
        if self.meanmedian:
            # already calculated
            return
        
        self.ndangerous = 0
        medianlist = list()
        for k, rel in self.relations.items():
            if rel.is_dangerous():
                self.ndangerous += 1
            rel.calc()
            medianlist.append(rel.median)
        
        if medianlist:
            self.meanmedian = round(float(np.mean(medianlist)), 3)
            self.doublemedian = int(np.median(medianlist))
        else:
            self.meanmedian = 0
            self.doublemedian = 0
        
        reviews_per_user = dict()
        for rel in self.relations.values():
            for u in rel.users():
                if u.public_id not in reviews_per_user:
                    reviews_per_user[u.public_id] = u.nreviews()

        if reviews_per_user:
            self.nusers = len(reviews_per_user)
            self.nreviews = sum(reviews_per_user.values())
            self.meanreviews = round(float(np.mean(list(reviews_per_user.values()))), 3)
            self.medianreviews = int(np.median(list(reviews_per_user.values())))

        # count list of all dangerous users
        for rel in self.dangerous():
            for u in rel.users():
                self.dangerous_users.add(u.public_id)

        self.nrisk_users = int(100*len(self.dangerous_users) / self.nusers)

    def __repr__(self):
        self.calc()
        return f"RELATIONS: {len(self.relations)} meanmedian: {self.meanmedian} doublemedian: {self.doublemedian} ndangerous: {self.ndangerous}" \
        f" riskusers:{len(self.dangerous_users)}/{self.nusers}={self.nrisk_users}% reviews total: {self.nreviews} mean:{self.meanreviews:.1f} median:{self.medianreviews}"

    def dangerous(self, field='count'):
        filtered = (rel for rel in self.relations.values() if rel.is_dangerous())  # Filter dangerous items
        sorted_items = sorted(filtered, key=lambda x: getattr(x, field), reverse=True)  # Sort descending
        yield from sorted_items


    def dump_table(self):
        console = Console()
        table = Table(show_header=True, header_style="bold magenta", title=f"{self.c.get_title()} ({self.c.address}) {self.c.object_id}")
        table.add_column("T", style='red')
        table.add_column("Company name")
        table.add_column("Town")
        table.add_column("ID/Alias")
        table.add_column("Hits")
        #table.add_column("Mean")
        table.add_column("Median")
        table.add_column("Rating")

        for rel in sorted(self.relations.values(), key=lambda x: x.count, reverse=True):
            rel.calc()
            # hide if not dangerous and low count
            if not rel.is_dangerous() and rel.count < settings.show_hit_th:
                continue
            _c = Company(rel.b)

            if rel.is_dangerous():
                tags_cell = Text(f"{_c.tags or ''}*")
            else:
                tags_cell = _c.tags

            if rel.count > settings.risk_hit_th:
                hits_cell = Text(f"{rel.count}", style='red')
            else:
                hits_cell = Text(str(rel.count), style="green")

            if rel.median < settings.risk_median_th:
                median_cell = Text(str(rel.median), style='red')
            else:
                median_cell = Text(str(rel.median), style='green')

            if rel.avg_arating >= settings.risk_highrate_th and rel.avg_brating >= settings.risk_highrate_th:
                rating_cell = Text(f"{rel.avg_arating:.1f} {rel.avg_brating:.1f}", style='red')
            else:
                rating_cell = Text(f"{rel.avg_arating:.1f} {rel.avg_brating:.1f}")

            table.add_row(tags_cell, _c.get_title(), _c.get_town(), _c.alias or Text(_c.object_id, style='grey30'), hits_cell,
                          # f"{rel.mean:.1f}", 
                          median_cell, rating_cell)
        print()
        console.print(table)

        print("added:", users_added)

    def export(self):
        rellist = list()

        for rel in sorted(self.relations.values(), key=lambda x: x.count, reverse=True):
            rel.calc()

            # hide if not dangerous and low count
            if not rel.is_dangerous() and rel.count < settings.show_hit_th:
                continue
            try:
                _c = Company(rel.b)
            except AFNoCompany:
                print(f"Ignore NO-COMPANY {rel.b} with {rel.count} hits")
                continue
            data = dict()
            data['tags'] = _c.tags
            data['title'] = _c.get_title()
            data['town'] = _c.get_town()
            data['alias'] = _c.alias
            data['oid'] = _c.object_id
            data['hits'] = rel.count
            data['median'] = rel.median
            data['arating'] = rel.avg_arating
            data['brating'] = rel.avg_brating
            rellist.append(data)
        return rellist


