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
        self.low_rating = 0

    def feed(self, cr: Review, empty: bool = False):

        if empty:
            return

        u = cr.user

        if cr.rating >= settings.risk_highrate_th:
            user_age = (cr.created - u.birthday()).days
            self.user_ages.append(user_age)
            self.records.append(f"{u.public_id} ({u.name} {cr.created_str} - {u.birthday_str}) = {user_age}")
        else:
            self.low_rating += 1


    def get_score(self):

        if len(self.user_ages) == 0:
            return self.score
        
        median_age = int(np.median(self.user_ages))

        self.score['median_user_age'] = median_age
        
        if len(self.user_ages) > settings.median_user_age_nusers and self.score['median_user_age'] <= settings.median_user_age:
            self.score['ma_low_rating'] = self.low_rating
            self.score['detections'].append(f"median_user_age {self.score['median_user_age']} <= {settings.median_user_age} ({sum(a <= settings.median_user_age for a in self.user_ages)} of {len(self.user_ages)})")
    
        return self.score
    
    def explain(self, fh):
        print(f"Explanation for median_user_age", file=fh)

        for idx, line in enumerate(self.records, start=1):
            print(f'{idx} {line}', file=fh)

        print(f"reviews with low rating: {self.score['ma_low_rating']}", file=fh)
        print(f"ages ({len(self.user_ages)}): {sorted(self.user_ages)}", file=fh)
        print(f"median age: {self.score['median_user_age']}", file=fh)
        print("", file=fh)
