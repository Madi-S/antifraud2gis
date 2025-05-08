from collections import Counter
from rich import print_json
import numpy as np


from .fd import BaseFD
from ..user import User, get_user
from ..company import Company
from ..companydb import get_by_oid
from ..review import Review
from ..settings import settings
from ..relation import RelationDict



"""
    test companies for relation (detect): 
    2956015537022403

    rshb for titles
"""

class RelationFD(BaseFD):

    def __init__(self, c, explain: bool = False):
        super().__init__(c, explain=explain)
        self.rpu = list()
        self.records = list()
        self._c.relations = RelationDict(c)

        self.happy_hirel_companies = list()

        self.towns = set()
        self.titles = set()

        self.processed_users = 0
        self.risk_users = dict()


    def feed(self, cr: Review, empty: bool = False):

        if empty:
            return


        u: User = cr.user
        for r in u.reviews():

            if r.oid == self._c.object_id:
                continue

            rel = self._c.relations[r.oid]
            rel.hit(cr.rating, r)

        self.processed_users += 1

        #if self.explain:
        #    self.records.append(f"{u.public_id} {u.name} {cr.rating} {u.nreviews()}")

    def get_score(self):
        self._c.relations.calc()

        if self.processed_users == 0:
            return self.score

        # hirel: relations with high hits and high ratings
        self.happy_hirel = 0
        self.hirel = 0

        towncount = self._c.relations.get_towns(risk=True)

        if towncount:
            top_town = max(towncount, key=towncount.get)
            top_towns_rels = towncount[top_town]
            # long_rels: count of risk (happy/high) relations WITHOUT top_town relations
            long_rels = sum(towncount.values()) - top_towns_rels

        for rel in self._c.relations.relations.values():
            if rel.check_high_hits():
                self.hirel += 1
                if rel.check_high_ratings():
                    self.happy_hirel += 1
                    self.happy_hirel_companies.append(rel.b)
                    self.towns.add(rel.get_btown())                    
                    self.titles.add(rel.get_btitle())

                    for u in rel.users():
                        if u.public_id not in self.risk_users:
                            self.risk_users[u.public_id] = list()
                        self.risk_users[u.public_id].append(rel.b)

        self.score['happy_ratio'] = int(100*self.happy_hirel/self.hirel) if self.hirel > 0 else 0
        self.score['happy_long_rel'] = int((100*long_rels)/self.happy_hirel) if self.happy_hirel > 0 else 0

        self.score['sametitle_rel'] = int(100*len(self.titles)/self.happy_hirel) if self.happy_hirel > 0 else 0
        self.score['risk_users'] = int(100*len(self.risk_users) / self.processed_users)

        if len(self.towns) >= settings.happy_long_rel_min_towns \
                and self.score['happy_ratio'] >= settings.happy_long_rel_happy_ratio \
                and self.score['happy_long_rel'] >= settings.happy_long_rel:
            self.score['detections'].append(f"happy_long_rel {self.score['happy_long_rel']}% ({long_rels} / {self.happy_hirel})")

        if self.happy_hirel >= settings.sametitle_rel and self.score['sametitle_rel'] <= settings.sametitle_ratio:
            self.score['detections'].append(f"sametitle_rel {self.score['sametitle_rel']}% ({self.happy_hirel} of {len(self.titles)})")

        elif self.score['risk_users'] > settings.risk_user_ratio:
            self.score['detections'].append(f"risk_users {self.score['risk_users']}% ({len(self.risk_users)} / {self.processed_users})")

        return self.score
    
    def explain(self, fh):
        print(f"Explanation for relations", file=fh)

        # explain hirel


        for dline in self.score['detections']:
            dname = dline.split()[0]
            print(f"DETECTION: {dname}", file=fh)

            if dname == 'happy_long_rel':                
                print(f"Towns ({len(self.towns)} >= {settings.happy_long_rel_min_towns}): {self.towns} ", file=fh)
                print(f"happy_long_rel is {len(self.towns)}/{self.happy_hirel} = {self.score['happy_long_rel']}% > {settings.happy_long_rel}", file=fh)
                print(file=fh)

            if dname == 'sametitle_rel':
                print(f"Titles: {len(self.titles)}", file=fh)
                print(f"Hirel ({self.happy_hirel} >= {settings.sametitle_rel}) and sametitle_rel {self.score['sametitle_rel']}% <= {settings.sametitle_ratio}%", file=fh)
                print(f"sametitle_rel is {len(self.titles)}/{self.happy_hirel} = {self.score['sametitle_rel']}%", file=fh)
                print(file=fh)


            if dname == 'risk_users':
                print(f"Risk users ({len(self.risk_users)} / {self.processed_users} > {settings.risk_user_ratio}%)", file=fh)

                for idx, public_id in enumerate(self.risk_users.keys(), start=1):
                    u = get_user(public_id)
                    print(f"user #{idx}. {public_id} {u.name} ({len(self.risk_users[public_id])}):", file=fh)
                    for oid in self.risk_users[public_id]:
                        crec = get_by_oid(oid)
                        if crec:
                            print(f"    {oid} {crec['title']} {crec['address']}", file=fh)
                        else:
                            print(f"    {oid} [special-not-a-company]", file=fh)
                
                print(f"{len(self.risk_users)} / {self.processed_users} = {self.score['risk_users']}%", file=fh)
                print("", file=fh)

        for line in self.records:
            print(line, file=fh)
            print("", file=fh)
