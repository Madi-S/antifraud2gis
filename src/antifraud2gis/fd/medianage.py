from collections import Counter
import numpy as np


from .fd import BaseFD
from ..user import User
from ..company import Company
from ..review import Review
from ..settings import settings

"""
    test companies for medianage (detect): 
    141265770459735
    70000001043693695 
    70000001074538667
"""

class MedianAgeFD(BaseFD):

    def __init__(self, c, explain: bool = False):
        super().__init__(c, explain=explain)
        self.user_ages = list()
        self.records = list()


    def feed(self, cr: Review, empty: bool = False):

        if empty:
            return

        u = cr.user

        if cr.rating >= settings.risk_highrate_th:
            user_age = (cr.created - u.birthday()).days
            self.user_ages.append(user_age)
            self.records.append(f"{u.public_id} ({u.name} {cr.created_str} - {u.birthday_str}) = {user_age}")


    def get_score(self):

        median_age = int(np.median(self.user_ages))

        self.score['median_user_age'] = median_age
        
        if len(self.user_ages) > settings.median_user_age_nusers and self.score['median_user_age'] <= settings.median_user_age:
            self.score['detections'].append(f"median_user_age {self.score['median_user_age']} <= {settings.median_user_age} ({sum(a <= settings.median_user_age for a in self.user_ages)} of {len(self.user_ages)})")
    
        return self.score
    
    def explain(self, fh):
        print(f"Explanation for median_user_age", file=fh)

        for line in self.records:
            print(line, file=fh)

        print(f"ages ({self.score['median_user_age']}): {sorted(self.user_ages)}", file=fh)
        print(f"result: {self.score['median_user_age']}", file=fh)
        print("", file=fh)
