from collections import Counter
import numpy as np


from .fd import BaseFD
from ..user import User
from ..company import Company
from ..review import Review
from ..settings import settings
from ..logger import logger

"""
    test companies for medianrpu (detect): 
    141265770459735
"""

class MedianRPUFD(BaseFD):

    def __init__(self, c, explain: bool = False):
        super().__init__(c, explain=explain)
        # self.rpu = list()
        self.records = list()
        self.rpu_list = list()
        self.lrpu_ratings = list()
        self.hrpu_ratings = list()


    def feed(self, cr: Review, empty: bool = False):

        if empty:
            return

        u = cr.user
        # self.rpu.append(u.nreviews())
        self.rpu_list.append(u.nreviews())
        if u.nreviews() <= settings.median_rpu:
            self.lrpu_ratings.append(cr.rating)
        else:
            self.hrpu_ratings.append(cr.rating)

        if self.explain and u.nreviews() <= settings.median_rpu:
            self.records.append(f"{u.public_id} {u.name} rating: {cr.rating} num_reviews: {u.nreviews()}")

    def get_score(self):

        self.median_rpu = int(np.median(self.rpu_list))

        self.low_rpu_rating = round(np.mean(self.lrpu_ratings), 1) if self.lrpu_ratings else 0
        self.high_rpu_rating = round(np.mean(self.hrpu_ratings), 1) if self.hrpu_ratings else 0
        self.rating_diff = round(self.low_rpu_rating - self.high_rpu_rating, 1)

        logger.debug(f"median_rpu: {self.median_rpu} threshold: {settings.median_rpu}")
        logger.debug(f"low_rpu_rating: {self.low_rpu_rating} - high_rpu_rating: {self.high_rpu_rating} = {self.rating_diff} ({settings.rating_diff})")

        self.score['median_rpu'] = f"{self.median_rpu} ({len(self.lrpu_ratings)}/{len(self.lrpu_ratings + self.hrpu_ratings)} users has RPU < {settings.median_rpu})"
        
        if self.median_rpu <= settings.median_rpu and self.rating_diff > settings.rating_diff:
            self.score['detections'].append(f"median_rpu: {self.median_rpu} <= {settings.median_rpu} "\
                f"({len(self.lrpu_ratings)} of {len(self.lrpu_ratings + self.hrpu_ratings)} users) rdiff: {self.rating_diff}")
    
        return self.score
    
    def explain(self, fh):
        print(f"Explanation for median_rpu", file=fh)

        for line in self.records:
            print(line, file=fh)

        print(f"RPUs ({len(self.rpu_list)}): {sorted(self.rpu_list)}", file=fh)
        print(f"result: {self.score['median_rpu']}", file=fh)
        print(f"rdiff: {self.low_rpu_rating} - {self.high_rpu_rating} = {self.rating_diff} > {settings.rating_diff}", file=fh)
        print("", file=fh)